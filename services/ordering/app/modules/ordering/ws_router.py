"""WebSocket hub: local sockets plus Redis fan-out so every ordering worker sees events."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections import defaultdict
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from smartserve_shared.routing import APIRouter

router = APIRouter()
logger = structlog.get_logger()

WS_CHANNEL_PREFIX = "ws:"
WS_CHANNEL_PATTERN = "ws:*"
PING_INTERVAL_SECONDS = 25.0

_connections: dict[str, set[WebSocket]] = defaultdict(set)
_redis: Any = None


def bind_redis(client: Any) -> None:
    global _redis
    _redis = client


def redis_client() -> Any:
    return _redis


def channel_for(location_id: str) -> str:
    return f"{WS_CHANNEL_PREFIX}{location_id}"


def location_id_from_channel(channel: str | bytes | None) -> str | None:
    if channel is None:
        return None
    raw = channel.decode() if isinstance(channel, bytes) else channel
    if not raw.startswith(WS_CHANNEL_PREFIX):
        return None
    location_id = raw[len(WS_CHANNEL_PREFIX) :]
    return location_id or None


def register(location_id: str, websocket: WebSocket) -> None:
    _connections[location_id].add(websocket)


def unregister(location_id: str, websocket: WebSocket) -> None:
    _connections[location_id].discard(websocket)
    if not _connections[location_id]:
        _connections.pop(location_id, None)


@router.websocket("/{location_id}")
async def websocket_endpoint(websocket: WebSocket, location_id: str) -> None:
    worker_id = str(os.getpid())
    await websocket.accept(headers=[(b"x-worker-id", worker_id.encode())])
    register(location_id, websocket)
    await websocket.send_json({"type": "hello", "workerId": worker_id, "locationId": location_id})
    logger.info("WebSocket connected", location_id=location_id, worker_id=worker_id)
    ping_task = asyncio.create_task(_ping_loop(websocket, location_id))
    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", location_id=location_id)
    except Exception:  # noqa: BLE001 — drop the socket on any receive failure
        logger.info("WebSocket closed with error", location_id=location_id, exc_info=True)
    finally:
        ping_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ping_task
        unregister(location_id, websocket)


async def _ping_loop(websocket: WebSocket, location_id: str) -> None:
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            try:
                await websocket.send_json({"type": "ping", "locationId": location_id})
            except Exception:  # noqa: BLE001 — treat send failure as a dead socket
                unregister(location_id, websocket)
                with contextlib.suppress(Exception):
                    await websocket.close()
                return
    except asyncio.CancelledError:
        raise


async def broadcast(location_id: str, event: dict) -> None:
    """Push a JSON event to sockets connected to this worker for `location_id`."""
    living = set(_connections.get(location_id, ()))
    for ws in living:
        try:
            await ws.send_json(event)
        except Exception:  # noqa: BLE001 — drop sockets that can no longer send
            unregister(location_id, ws)


async def publish_ws(location_id: str, event: dict) -> None:
    """Publish to Redis so every ordering worker can push to its own sockets."""
    client = redis_client()
    if client is None:
        await broadcast(location_id, event)
        return
    await client.publish(channel_for(location_id), json.dumps(event))


async def handle_redis_message(message: dict[str, Any]) -> None:
    kind = message.get("type")
    if kind not in ("message", "pmessage"):
        return
    location_id = location_id_from_channel(message.get("channel"))
    if not location_id:
        return
    raw = message.get("data")
    if raw is None:
        return
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("ws.redis: dropping unparsable fan-out message")
        return
    if not isinstance(event, dict):
        return
    await broadcast(location_id, event)


async def subscribe_ws_forever() -> None:
    """PSUBSCRIBE `ws:*` and forward each message to this worker's sockets."""
    client = redis_client()
    if client is None:
        raise RuntimeError("redis is not bound")
    pubsub = client.pubsub()
    await pubsub.psubscribe(WS_CHANNEL_PATTERN)
    async for message in pubsub.listen():
        await handle_redis_message(message)

"""WebSocket hub: local sockets plus Redis fan-out so every ordering worker sees events."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
from collections import defaultdict
from typing import Any

import httpx
import structlog
from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from smartserve_shared.routing import APIRouter
from smartserve_shared.tenancy import verify_location_owned

from app.api.v1.deps import get_current_user
from app.clients import auth_client
from app.db.models import Location, User
from app.db.session import DbSession
from app.modules.ordering.schemas import WsTicketIn, WsTicketOut

router = APIRouter()
logger = structlog.get_logger()

WS_CHANNEL_PREFIX = "ws:"
WS_CHANNEL_PATTERN = "ws:*"
PING_INTERVAL_SECONDS = 25.0
TICKET_TTL_SECONDS = 60
TICKET_KEY_PREFIX = "ws:ticket:"
WS_UNAUTHORIZED = 4401
_SOCKET_DEVICE_TYPES = frozenset({"kds", "display"})

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


def _ticket_key(ticket: str) -> str:
    return f"{TICKET_KEY_PREFIX}{ticket}"


async def issue_ws_ticket(location_id: str) -> str:
    client = redis_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Realtime unavailable")
    raw = secrets.token_urlsafe(32)
    await client.set(_ticket_key(raw), location_id, ex=TICKET_TTL_SECONDS)
    return raw


async def consume_ws_ticket(ticket: str | None) -> str | None:
    if not ticket:
        return None
    client = redis_client()
    if client is None:
        return None
    value = await client.getdel(_ticket_key(ticket))
    if isinstance(value, bytes):
        return value.decode()
    return value


async def device_for_token(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        resp = await auth_client.get("/api/v1/devices/current", headers={"X-Device-Token": raw})
    except httpx.HTTPStatusError, httpx.RequestError:
        return None
    body = resp.json()
    return body if isinstance(body, dict) else None


async def authorize_socket(websocket: WebSocket, location_id: str) -> bool:
    ticket = websocket.query_params.get("ticket")
    if ticket:
        ticket_location = await consume_ws_ticket(ticket)
        return ticket_location == location_id
    raw = websocket.query_params.get("deviceToken") or websocket.headers.get("x-device-token")
    device = await device_for_token(raw)
    if not device:
        return False
    device_location = device.get("locationId") or device.get("location_id")
    device_type = device.get("type")
    return device_location == location_id and device_type in _SOCKET_DEVICE_TYPES


@router.post("/ticket", response_model=WsTicketOut)
async def create_ws_ticket(
    data: WsTicketIn,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> WsTicketOut:
    await verify_location_owned(db, data.location_id, current_user.business_id, Location)
    ticket = await issue_ws_ticket(data.location_id)
    return WsTicketOut(ticket=ticket, expires_in=TICKET_TTL_SECONDS)


@router.websocket("/{location_id}")
async def websocket_endpoint(websocket: WebSocket, location_id: str) -> None:
    if not await authorize_socket(websocket, location_id):
        await websocket.close(code=WS_UNAUTHORIZED)
        return
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

"""WebSocket endpoint for real-time order and KDS events.

Migrated from apps/api as part of Step 25 (monolith retirement) — `ordering` is the
natural owner since it's the only service whose state changes (new orders, fired
courses, status transitions) these events describe.
"""

from collections import defaultdict

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from app.api.v1.router_base import APIRouter

router = APIRouter()
logger = structlog.get_logger()

# Simple in-process connection manager (replace with Redis pub/sub in a future step)
_connections: dict[str, list[WebSocket]] = defaultdict(list)


@router.websocket("/{location_id}")
async def websocket_endpoint(websocket: WebSocket, location_id: str):
    await websocket.accept()
    _connections[location_id].append(websocket)
    logger.info("WebSocket connected", location_id=location_id)
    try:
        while True:
            # Keep connection alive; actual events are pushed from order endpoints
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[location_id].remove(websocket)
        logger.info("WebSocket disconnected", location_id=location_id)


async def broadcast(location_id: str, event: dict) -> None:
    """Broadcast a JSON event to all connected clients for a location."""
    dead = []
    for ws in _connections[location_id]:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections[location_id].remove(ws)

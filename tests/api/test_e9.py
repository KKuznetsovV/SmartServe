"""E9: two ordering workers both receive committed order events over the WebSocket hub."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
import websockets
from httpx import AsyncClient

from conftest import API_BASE_URL, add_item, create_order, submit_order
from test_s4 import _ws_url


@pytest.mark.stack
async def test_e9_two_sockets_see_submitted_order(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_id = waiter_a["locationId"]
    token = waiter_a["token"]
    url = _ws_url(location_id)

    async with (
        websockets.connect(url, open_timeout=10) as first,
        websockets.connect(url, open_timeout=10) as second,
    ):
        order = await create_order(client, token, location_id)
        await add_item(client, token, order["id"], catalog["burgerId"])
        submitted = await submit_order(client, token, order["id"])
        assert submitted["status"] == "submitted"

        seen_first = await _wait_for_order(first, order["id"])
        seen_second = await _wait_for_order(second, order["id"])
        assert seen_first["type"].startswith("order.")
        assert seen_second["type"].startswith("order.")
        for payload in (seen_first["payload"], seen_second["payload"]):
            assert payload.get("orderId") == order["id"] or payload.get("id") == order["id"]
            assert "total" not in payload
            assert "notes" not in payload
            assert "createdBy" not in payload


async def _wait_for_order(ws: websockets.ClientConnection, order_id: str, timeout: float = 15.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        raw = await asyncio.wait_for(ws.recv(), timeout=max(remaining, 0.1))
        if isinstance(raw, bytes):
            raw = raw.decode()
        msg = json.loads(raw)
        if msg.get("type") == "ping":
            continue
        payload = msg.get("payload") or {}
        if payload.get("orderId") == order_id or payload.get("id") == order_id:
            return msg
    raise AssertionError(f"no websocket event for order {order_id}")

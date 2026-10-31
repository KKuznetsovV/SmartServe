"""E9: two ordering workers both receive committed order events over the WebSocket hub."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
import websockets
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order, submit_order
from test_s4 import connect_location_ws

_CONTROL_TYPES = {"hello", "ping"}


@pytest.mark.stack
async def test_e9_two_sockets_see_submitted_order(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_id = waiter_a["locationId"]
    token = waiter_a["token"]
    first, second, first_id, second_id = await _connect_distinct_workers(
        lambda: connect_location_ws(client, token, location_id)
    )
    try:
        assert first_id != second_id
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
    finally:
        await first.close()
        await second.close()


@pytest.mark.stack
async def test_e9_failed_commit_is_not_broadcast(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_id = waiter_a["locationId"]
    token = waiter_a["token"]
    order = await create_order(client, token, location_id)
    await add_item(client, token, order["id"], catalog["burgerId"])

    first, second, first_id, second_id = await _connect_distinct_workers(
        lambda: connect_location_ws(client, token, location_id)
    )
    try:
        assert first_id != second_id
        # Create/add enqueue outbox events that may arrive after the sockets open.
        await asyncio.gather(_drain_until_quiet(first), _drain_until_quiet(second))
        failed = await client.post(
            f"/orders/{order['id']}/submit",
            headers={**bearer(token), "X-Fail-Commit": "1"},
        )
        assert failed.status_code >= 500 or failed.status_code == 409
        still_open = await get_order(client, token, order["id"])
        assert still_open["status"] == "open"

        await asyncio.gather(_assert_no_domain_events(first), _assert_no_domain_events(second))

        submitted = await submit_order(client, token, order["id"])
        assert submitted["status"] == "submitted"
        seen_first = await _wait_for_order(first, order["id"])
        seen_second = await _wait_for_order(second, order["id"])
        assert seen_first["type"].startswith("order.")
        assert seen_second["type"].startswith("order.")
    finally:
        await first.close()
        await second.close()


async def _connect_distinct_workers(
    connect, *, attempts: int = 20
) -> tuple[websockets.ClientConnection, websockets.ClientConnection, str, str]:
    first = await connect()
    first_id = await _worker_id(first)
    try:
        for _ in range(attempts):
            candidate = await connect()
            candidate_id = await _worker_id(candidate)
            if candidate_id != first_id:
                return first, candidate, first_id, candidate_id
            await candidate.close()
    except Exception:
        await first.close()
        raise
    await first.close()
    raise AssertionError(f"could not land sockets on different workers after {attempts} attempts (kept {first_id})")


async def _worker_id(ws: websockets.ClientConnection) -> str:
    header = ""
    response = getattr(ws, "response", None)
    if response is not None:
        header = response.headers.get("X-Worker-Id") or response.headers.get("x-worker-id") or ""
    raw = await asyncio.wait_for(ws.recv(), timeout=5)
    if isinstance(raw, bytes):
        raw = raw.decode()
    msg = json.loads(raw)
    assert msg.get("type") == "hello", msg
    hello_id = str(msg.get("workerId") or "")
    worker = header or hello_id
    assert worker
    if header and hello_id:
        assert header == hello_id
    return worker


async def _wait_for_order(ws: websockets.ClientConnection, order_id: str, timeout: float = 15.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        raw = await asyncio.wait_for(ws.recv(), timeout=max(remaining, 0.1))
        if isinstance(raw, bytes):
            raw = raw.decode()
        msg = json.loads(raw)
        if msg.get("type") in _CONTROL_TYPES:
            continue
        payload = msg.get("payload") or {}
        if payload.get("orderId") == order_id or payload.get("id") == order_id:
            return msg
    raise AssertionError(f"no websocket event for order {order_id}")


async def _drain_until_quiet(ws: websockets.ClientConnection, timeout: float = 2.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return
        try:
            await asyncio.wait_for(ws.recv(), timeout=remaining)
        except TimeoutError:
            return


async def _assert_no_domain_events(ws: websockets.ClientConnection, timeout: float = 3.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except TimeoutError:
            return
        if isinstance(raw, bytes):
            raw = raw.decode()
        msg = json.loads(raw)
        kind = str(msg.get("type") or "")
        if kind in _CONTROL_TYPES:
            continue
        if kind.startswith("order.") or "discount" in kind:
            raise AssertionError(f"unexpected websocket event after failed commit: {msg}")

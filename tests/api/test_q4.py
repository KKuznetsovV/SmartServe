import os

import pytest
from httpx import AsyncClient

from conftest import add_item, create_order, get_order, set_item_status, submit_order
from test_e9 import _drain_until_quiet, _wait_for_order, _worker_id
from test_s4 import connect_location_ws


async def test_q4_cancelling_item_lowers_total(
    client: AsyncClient, waiter_a: dict, kitchen_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    first = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    before = submitted["total"]
    await set_item_status(client, kitchen_a["token"], submitted["id"], first["id"], "cancelled")
    after = await get_order(client, waiter_a["token"], submitted["id"])
    assert after["total"] < before


@pytest.mark.stack
async def test_q4_cancel_broadcasts_order_updated(
    client: AsyncClient, waiter_a: dict, kitchen_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    location_id = waiter_a["locationId"]
    ws = await connect_location_ws(client, waiter_a["token"], location_id)
    try:
        await _worker_id(ws)
        order = await create_order(client, waiter_a["token"], location_id)
        first = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
        await add_item(client, waiter_a["token"], order["id"], catalog["burgerId"])
        submitted = await submit_order(client, waiter_a["token"], order["id"])
        await _drain_until_quiet(ws)
        await set_item_status(client, kitchen_a["token"], submitted["id"], first["id"], "cancelled")
        msg = await _wait_for_order(ws, submitted["id"], timeout=2.0)
        assert msg["type"] == "order.updated"
        payload = msg.get("payload") or {}
        assert payload.get("orderId") == submitted["id"] or payload.get("id") == submitted["id"]
        assert "total" not in payload
    finally:
        await ws.close()

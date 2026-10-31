import os

import pytest
from httpx import AsyncClient

from conftest import bearer, create_order, get_order
from test_e9 import _drain_until_quiet, _wait_for_order, _worker_id
from test_s4 import connect_location_ws


async def test_q2_order_includes_table_name(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    table = catalog["table"]
    order = await create_order(
        client,
        waiter_a["token"],
        waiter_a["locationId"],
        table_id=table["id"],
        channel="dine_in",
        guest_count=2,
    )
    assert order["tableName"]
    assert order["tableName"] == table["name"]

    takeaway = await create_order(
        client,
        waiter_a["token"],
        waiter_a["locationId"],
        channel="takeaway",
    )
    assert takeaway["tableName"] is None


@pytest.mark.stack
async def test_q2_table_name_on_get_list_and_kds_socket(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    token = waiter_a["token"]
    location_id = waiter_a["locationId"]
    headers = bearer(token)
    tables = await client.get(f"/locations/{location_id}/tables", headers=headers)
    tables.raise_for_status()
    t3 = next(t for t in tables.json() if t["name"] == "T3")

    ws = await connect_location_ws(client, token, location_id)
    try:
        await _worker_id(ws)
        await _drain_until_quiet(ws)
        order = await create_order(
            client,
            token,
            location_id,
            table_id=t3["id"],
            channel="dine_in",
            guest_count=2,
        )
        detail = await get_order(client, token, order["id"])
        assert detail["tableName"] == "T3"

        listed = await client.get(f"/locations/{location_id}/orders", headers=headers)
        listed.raise_for_status()
        match = next(row for row in listed.json() if row["id"] == order["id"])
        assert match["tableName"] == "T3"

        msg = await _wait_for_order(ws, order["id"], timeout=5.0)
        payload = msg.get("payload") or {}
        assert payload.get("tableName") == "T3"
    finally:
        await ws.close()

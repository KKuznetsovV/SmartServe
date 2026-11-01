"""Pre-E5 queues (no DLX args) must not block consumers; payment still marks the order paid."""

from __future__ import annotations

import asyncio
import os

import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order, submit_order


@pytest.mark.stack
async def test_payment_marks_order_paid_against_pre_e5_queues(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    if os.environ.get("SMARTSERVE_STACK") != "1":
        pytest.skip("stack-only: set SMARTSERVE_STACK=1 in the compose API suite")

    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    paid = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": submitted["id"], "method": "cash", "amount": submitted["total"]},
    )
    assert paid.status_code == 201, paid.text
    refreshed = submitted
    for _ in range(40):
        refreshed = await get_order(client, waiter_a["token"], submitted["id"])
        if refreshed["status"] == "paid":
            break
        await asyncio.sleep(0.25)
    assert refreshed["status"] == "paid"

import asyncio

import pytest
from httpx import AsyncClient

from conftest import add_item, create_order, get_order


async def test_e6_concurrent_adds_match_line_sum(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])

    async def add_cola() -> None:
        await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])

    await asyncio.gather(*(add_cola() for _ in range(20)))
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    line_sum = sum(item["unitPrice"] * item["qty"] for item in refreshed["items"])
    assert refreshed["subtotal"] == pytest.approx(line_sum)
    assert len(refreshed["items"]) == 20

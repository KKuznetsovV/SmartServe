import pytest
from httpx import AsyncClient

from conftest import add_item, create_order, get_order, set_item_status, submit_order


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

import asyncio

from httpx import AsyncClient

from conftest import add_item, create_order, get_order, set_item_status, submit_order


async def test_e4_kitchen_ready_stays_ready(
    client: AsyncClient, waiter_a: dict, kitchen_a: dict, catalog: dict
) -> None:
    location_id = waiter_a["locationId"]
    orders: list[dict] = []
    for _ in range(20):
        order = await create_order(client, waiter_a["token"], location_id)
        await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
        submitted = await submit_order(client, waiter_a["token"], order["id"])
        orders.append(submitted)

    for order in orders:
        for item in order["items"]:
            await set_item_status(client, kitchen_a["token"], order["id"], item["id"], "ready")

    await asyncio.sleep(1)

    for order in orders:
        refreshed = await get_order(client, kitchen_a["token"], order["id"])
        assert refreshed["status"] == "ready"

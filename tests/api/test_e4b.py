import asyncio

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order, submit_order


async def test_e4b_full_payment_marks_order_paid_within_two_seconds(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    location_id = waiter_a["locationId"]
    order = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])

    pay = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": submitted["id"], "method": "cash", "amount": submitted["total"]},
    )
    assert pay.status_code == 201
    body = pay.json()
    assert body["orderFullyPaid"] is True
    assert body["remaining"] == 0

    deadline = asyncio.get_event_loop().time() + 2
    refreshed = await get_order(client, waiter_a["token"], submitted["id"])
    while refreshed["status"] != "paid":
        if asyncio.get_event_loop().time() > deadline:
            break
        await asyncio.sleep(0.1)
        refreshed = await get_order(client, waiter_a["token"], submitted["id"])
    assert refreshed["status"] == "paid"


async def test_e4b_partial_payment_shows_remaining(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    location_id = waiter_a["locationId"]
    order = await create_order(client, waiter_a["token"], location_id)
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    half = round(submitted["total"] / 2, 2)
    expected_remaining = round(submitted["total"] - half, 2)

    pay = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": submitted["id"], "method": "cash", "amount": half},
    )
    assert pay.status_code == 201
    body = pay.json()
    assert body["orderFullyPaid"] is False
    assert body["remaining"] == expected_remaining

    refreshed = await get_order(client, waiter_a["token"], submitted["id"])
    assert refreshed["status"] != "paid"

from decimal import Decimal

from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order, submit_order


async def _category(client: AsyncClient, token: str, location_id: str, name: str) -> str:
    resp = await client.post(
        "/menu/categories",
        headers=bearer(token),
        json={"locationId": location_id, "name": name},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def _item(client: AsyncClient, token: str, category_id: str, name: str, price: float | str) -> str:
    resp = await client.post(
        "/menu/items",
        headers=bearer(token),
        json={"categoryId": category_id, "name": name, "price": price},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def test_e7_qty_line_is_exact(client: AsyncClient, owner_a: dict, waiter_a: dict) -> None:
    cat = await _category(client, owner_a["token"], owner_a["locationId"], "E7 cents")
    item_id = await _item(client, owner_a["token"], cat, "E7 10.10", "10.10")
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], item_id, qty=3)
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    assert refreshed["subtotal"] == 30.30
    assert refreshed["items"][0]["unitPrice"] == 10.10


async def test_e7_percent_discount_half_up(client: AsyncClient, owner_a: dict, waiter_a: dict) -> None:
    cat = await _category(client, owner_a["token"], owner_a["locationId"], "E7 half-up")
    item_id = await _item(client, owner_a["token"], cat, "E7 33.33", "33.33")
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    line = await add_item(client, waiter_a["token"], order["id"], item_id)
    resp = await client.post(
        f"/orders/{order['id']}/items/discount",
        headers=bearer(waiter_a["token"]),
        json={"items": [{"itemId": line["id"]}], "discountType": "percent", "discountValue": 15},
    )
    resp.raise_for_status()
    discounted = next(i for i in resp.json()["items"] if i["id"] == line["id"])
    assert discounted["discountAmount"] == 5.00


async def test_e7_exact_payment_and_one_cent_short(client: AsyncClient, waiter_a: dict, catalog: dict) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    await add_item(client, waiter_a["token"], order["id"], catalog["colaId"])
    submitted = await submit_order(client, waiter_a["token"], order["id"])
    total = Decimal(str(submitted["total"]))
    short = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": order["id"], "method": "cash", "amount": str(total - Decimal("0.01"))},
    )
    assert short.status_code == 201
    assert short.json()["orderFullyPaid"] is False
    assert short.json()["remaining"] == 0.01

    full = await client.post(
        "/payments",
        headers=bearer(waiter_a["token"]),
        json={"orderId": order["id"], "method": "cash", "amount": 0.01},
    )
    assert full.status_code == 201
    assert full.json()["orderFullyPaid"] is True
    assert full.json()["remaining"] == 0


async def test_e7_bulk_percent_on_twelve(client: AsyncClient, owner_a: dict) -> None:
    cat = await _category(client, owner_a["token"], owner_a["locationId"], "E7 bulk")
    item_id = await _item(client, owner_a["token"], cat, "E7 12.00", "12.00")
    resp = await client.post(
        "/menu/items/bulk-price",
        headers=bearer(owner_a["token"]),
        json={"locationId": owner_a["locationId"], "categoryId": cat, "changePct": 10},
    )
    resp.raise_for_status()
    listed = await client.get(f"/menu/items/{item_id}", headers=bearer(owner_a["token"]))
    listed.raise_for_status()
    assert listed.json()["price"] == 13.20

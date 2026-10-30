import pytest
from httpx import AsyncClient

from conftest import add_item, bearer, create_order, get_order


async def test_q6_split_prorates_discount_and_keeps_category(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    line = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"], qty=3)
    discounted = await client.post(
        f"/orders/{order['id']}/items/discount",
        headers=bearer(waiter_a["token"]),
        json={
            "items": [{"itemId": line["id"]}],
            "discountType": "fixed",
            "discountValue": 30,
        },
    )
    discounted.raise_for_status()

    split = await client.post(
        f"/orders/{order['id']}/items/assign-guests",
        headers=bearer(waiter_a["token"]),
        json={"assignments": [{"itemId": line["id"], "guestNumber": 1, "quantity": 1}]},
    )
    split.raise_for_status()
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    rows = [item for item in refreshed["items"] if item["menuItemId"] == catalog["colaId"]]
    assert len(rows) == 2
    by_qty = {item["qty"]: item for item in rows}
    assert by_qty[2]["discountAmount"] == pytest.approx(20)
    assert by_qty[1]["discountAmount"] == pytest.approx(10)
    assert by_qty[2]["categoryId"]
    assert by_qty[1]["categoryId"] == by_qty[2]["categoryId"]


async def test_q6_split_fixed_discount_remainder_stays_on_original(
    client: AsyncClient, waiter_a: dict, catalog: dict
) -> None:
    order = await create_order(client, waiter_a["token"], waiter_a["locationId"])
    line = await add_item(client, waiter_a["token"], order["id"], catalog["colaId"], qty=3)
    discounted = await client.post(
        f"/orders/{order['id']}/items/discount",
        headers=bearer(waiter_a["token"]),
        json={
            "items": [{"itemId": line["id"]}],
            "discountType": "fixed",
            "discountValue": 10,
        },
    )
    discounted.raise_for_status()

    split = await client.post(
        f"/orders/{order['id']}/items/assign-guests",
        headers=bearer(waiter_a["token"]),
        json={"assignments": [{"itemId": line["id"], "guestNumber": 1, "quantity": 1}]},
    )
    split.raise_for_status()
    refreshed = await get_order(client, waiter_a["token"], order["id"])
    rows = [item for item in refreshed["items"] if item["menuItemId"] == catalog["colaId"]]
    by_qty = {item["qty"]: item for item in rows}
    assert by_qty[2]["discountAmount"] == pytest.approx(6.67)
    assert by_qty[1]["discountAmount"] == pytest.approx(3.33)
    assert by_qty[2]["discountAmount"] + by_qty[1]["discountAmount"] == pytest.approx(10)

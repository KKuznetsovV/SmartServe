import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuCategory, MenuItem, User


@pytest.mark.asyncio
async def test_split_prorates_fixed_discount_remainder_on_original(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    category = MenuCategory(name="Mains")
    db.add(category)
    await db.flush()
    schnitzel = MenuItem(category_id=category.id, name="Schnitzel", price=50.0)
    db.add(schnitzel)
    await db.flush()

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()["id"]
    line = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": schnitzel.id, "qty": 3},
            headers=headers,
        )
    ).json()
    discounted = await client.post(
        f"/api/v1/orders/{order_id}/items/discount",
        json={"items": [{"itemId": line["id"]}], "discountType": "fixed", "discountValue": 10},
        headers=headers,
    )
    assert discounted.status_code == 200

    split = await client.post(
        f"/api/v1/orders/{order_id}/items/assign-guests",
        json={"assignments": [{"itemId": line["id"], "guestNumber": 1, "quantity": 1}]},
        headers=headers,
    )
    assert split.status_code == 200
    rows = [item for item in split.json()["items"] if item["menuItemId"] == schnitzel.id]
    assert len(rows) == 2
    by_qty = {item["qty"]: item for item in rows}
    assert by_qty[2]["discountAmount"] == pytest.approx(6.67)
    assert by_qty[1]["discountAmount"] == pytest.approx(3.33)
    assert by_qty[2]["discountAmount"] + by_qty[1]["discountAmount"] == pytest.approx(10)
    assert by_qty[1]["categoryId"] == category.id
    assert by_qty[2]["categoryId"] == category.id
    assert by_qty[1]["categoryName"] == "Mains"
    assert {by_qty[2]["discountAmount"], by_qty[1]["discountAmount"]} != {3.33}


@pytest.mark.asyncio
async def test_split_keeps_percent_discount_on_both_rows(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    category = MenuCategory(name="Mains")
    db.add(category)
    await db.flush()
    burger = MenuItem(category_id=category.id, name="Burger", price=60.0)
    db.add(burger)
    await db.flush()

    order_id = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "channel": "takeaway"},
            headers=headers,
        )
    ).json()["id"]
    line = (
        await client.post(
            f"/api/v1/orders/{order_id}/items",
            json={"menuItemId": burger.id, "qty": 3},
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/v1/orders/{order_id}/items/discount",
        json={"items": [{"itemId": line["id"]}], "discountType": "percent", "discountValue": 10},
        headers=headers,
    )
    split = await client.post(
        f"/api/v1/orders/{order_id}/items/assign-guests",
        json={"assignments": [{"itemId": line["id"], "guestNumber": 1, "quantity": 1}]},
        headers=headers,
    )
    assert split.status_code == 200
    rows = [item for item in split.json()["items"] if item["menuItemId"] == burger.id]
    by_qty = {item["qty"]: item for item in rows}
    assert by_qty[2]["discountType"] == "percent"
    assert by_qty[1]["discountType"] == "percent"
    assert by_qty[2]["discountValue"] == pytest.approx(10)
    assert by_qty[1]["discountValue"] == pytest.approx(10)
    assert by_qty[2]["discountAmount"] == pytest.approx(12)
    assert by_qty[1]["discountAmount"] == pytest.approx(6)

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Discount, Location, MenuItem, User


async def _order_with_item(
    client: AsyncClient,
    token: str,
    location_id: str,
    menu_item_id: str,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    order = await client.post(
        "/api/v1/orders",
        json={"locationId": location_id, "channel": "takeaway"},
        headers=headers,
    )
    assert order.status_code == 201
    order_id = order.json()["id"]
    added = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item_id, "qty": 1},
        headers=headers,
    )
    assert added.status_code == 201
    refreshed = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert refreshed.status_code == 200
    return refreshed.json()


@pytest.mark.asyncio
async def test_vat_inclusive_burger_68(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    burger = MenuItem(category_id="cat-1", name="Burger", price=68)
    db.add(burger)
    await db.flush()

    order = await _order_with_item(client, token, location.id, burger.id)
    assert order["total"] == 68.00
    assert order["taxAmount"] == 10.37
    assert order["vatRate"] == 0.18


@pytest.mark.asyncio
async def test_vat_happy10_on_100(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    item = MenuItem(category_id="cat-1", name="VAT 100", price=100)
    discount = Discount(business_id=business.id, code="HAPPY10", name="Happy hour 10%", type="percent", value=10)
    db.add_all([item, discount])
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}
    order = await _order_with_item(client, token, location.id, item.id)
    applied = await client.post(
        f"/api/v1/orders/{order['id']}/discount",
        json={"code": "HAPPY10"},
        headers=headers,
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["total"] == 90.00
    assert body["taxAmount"] == 13.73


@pytest.mark.asyncio
async def test_vat_zero_at_location(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location.vat_rate = Decimal("0")
    burger = MenuItem(category_id="cat-1", name="Burger", price=68)
    db.add(burger)
    await db.flush()

    order = await _order_with_item(client, token, location.id, burger.id)
    assert order["total"] == 68.00
    assert order["taxAmount"] == 0.00
    assert order["vatRate"] == 0.0


@pytest.mark.asyncio
async def test_changing_business_vat_does_not_rewrite_existing_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    burger = MenuItem(category_id="cat-1", name="Burger", price=68)
    db.add(burger)
    await db.flush()

    order = await _order_with_item(client, token, location.id, burger.id)
    assert order["taxAmount"] == 10.37

    business.vat_rate = Decimal("0")
    await db.flush()

    refreshed = await client.get(
        f"/api/v1/orders/{order['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["total"] == 68.00
    assert body["taxAmount"] == 10.37
    assert body["vatRate"] == 0.18

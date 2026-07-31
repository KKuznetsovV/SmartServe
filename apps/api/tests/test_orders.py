"""Integration tests for order lifecycle."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuCategory, MenuItem, User


@pytest.mark.asyncio
async def test_order_lifecycle(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()

    item = MenuItem(
        category_id=category.id,
        name="Burger",
        price=45.0,
        tax_rate=0.17,
        preparation_time_min=15,
    )
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    # Create order
    resp = await client.post(
        "/api/v1/orders",
        json={"location_id": location.id, "channel": "dine_in"},
        headers=headers,
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]
    assert resp.json()["status"] == "open"

    # Add item to order
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menu_item_id": item.id, "qty": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["menu_item_name"] == "Burger"

    # Submit order
    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    # Cannot submit again
    resp = await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 400

    # Cancel from submitted
    resp = await client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_payment_completes_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    category = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(category)
    await db.flush()
    item = MenuItem(category_id=category.id, name="Salad", price=30.0, tax_rate=0.17, preparation_time_min=5)
    db.add(item)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    order_resp = await client.post(
        "/api/v1/orders",
        json={"location_id": location.id, "channel": "takeaway"},
        headers=headers,
    )
    order_id = order_resp.json()["id"]

    await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menu_item_id": item.id, "qty": 1},
        headers=headers,
    )

    # Fetch order total
    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    total = order["total"]

    # Pay in full
    resp = await client.post(
        "/api/v1/payments",
        json={"order_id": order_id, "method": "card", "amount": total},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"

    # Order should now be paid
    order = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()
    assert order["status"] == "paid"

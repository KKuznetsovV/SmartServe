"""Tests for stock management endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuItem, User


@pytest.mark.asyncio
async def test_set_item_stock(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Default is in_stock=True
    assert menu_item.in_stock is True

    # Mark out of stock
    resp = await client.patch(
        f"/api/v1/menu/items/{menu_item.id}/stock",
        json={"inStock": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["inStock"] is False

    # Mark back in stock
    resp = await client.patch(
        f"/api/v1/menu/items/{menu_item.id}/stock",
        json={"inStock": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["inStock"] is True


@pytest.mark.asyncio
async def test_out_of_stock_blocks_order_add(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Mark item out of stock
    await client.patch(
        f"/api/v1/menu/items/{menu_item.id}/stock",
        json={"inStock": False},
        headers=headers,
    )

    # Create order and try to add out-of-stock item
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": 1},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "out of stock" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_location_stock(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/api/v1/menu/locations/{location.id}/stock", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any(i["id"] == menu_item.id for i in items)

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

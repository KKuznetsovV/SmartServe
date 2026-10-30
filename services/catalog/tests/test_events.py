"""Tests for catalog.item_updated outbox rows (no live broker)."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuCategory, MenuItem, Outbox, User


async def _latest_item_updated(db: AsyncSession) -> dict:
    db.expire_all()
    row = (await db.execute(select(Outbox).order_by(Outbox.occurred_at.desc()))).scalars().first()
    assert row is not None
    assert row.routing_key == "catalog.item_updated"
    return json.loads(row.payload)


@pytest.mark.asyncio
async def test_create_item_enqueues_catalog_item_updated(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    headers = {"Authorization": f"Bearer {token}"}
    cat = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(cat)
    await db.flush()

    resp = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat.id, "name": "Burger", "price": 50.0},
        headers=headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    payload = await _latest_item_updated(db)
    assert payload["itemId"] == item_id
    assert payload["price"] == 50.0
    assert payload["businessId"] == business_id
    assert payload["eventId"]


@pytest.mark.asyncio
async def test_update_item_enqueues_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    item_id = menu_item.id
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(f"/api/v1/menu/items/{item_id}", json={"price": 60.0}, headers=headers)
    assert resp.status_code == 200

    payload = await _latest_item_updated(db)
    assert payload["itemId"] == item_id
    assert payload["price"] == 60.0
    assert payload["businessId"] == business_id


@pytest.mark.asyncio
async def test_set_stock_enqueues_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    owner_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = owner_user
    business_id = user.business_id
    item_id = menu_item.id
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(f"/api/v1/menu/items/{item_id}/stock", json={"inStock": False}, headers=headers)
    assert resp.status_code == 200

    payload = await _latest_item_updated(db)
    assert payload["inStock"] is False
    assert payload["businessId"] == business_id


@pytest.mark.asyncio
async def test_bulk_price_update_enqueues_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    location: Location,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    location_id = location.id
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location_id, "changePct": 10},
        headers=headers,
    )
    assert resp.status_code == 200

    payload = await _latest_item_updated(db)
    assert payload["bulk"] is True
    assert payload["updated"] == 1
    assert payload["businessId"] == business_id

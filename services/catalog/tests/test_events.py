"""Tests for catalog.item_updated publish call sites (mocked mq.publish, no live broker)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.models import Location, MenuCategory, MenuItem, User


@pytest.mark.asyncio
async def test_create_item_publishes_catalog_item_updated(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
    db,
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    cat = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(cat)
    await db.flush()

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/menu/items",
            json={"categoryId": cat.id, "name": "Burger", "price": 50.0},
            headers=headers,
        )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "catalog.item_updated"
    assert payload["itemId"] == item_id
    assert payload["price"] == 50.0


@pytest.mark.asyncio
async def test_update_item_publishes_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.patch(f"/api/v1/menu/items/{menu_item.id}", json={"price": 60.0}, headers=headers)
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "catalog.item_updated"
    assert payload["itemId"] == menu_item.id
    assert payload["price"] == 60.0


@pytest.mark.asyncio
async def test_set_stock_publishes_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    owner_user: tuple[User, str],
):
    _, token = owner_user
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.patch(f"/api/v1/menu/items/{menu_item.id}/stock", json={"inStock": False}, headers=headers)
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "catalog.item_updated"
    assert payload["inStock"] is False


@pytest.mark.asyncio
async def test_bulk_price_update_publishes_catalog_item_updated(
    client: AsyncClient,
    menu_item: MenuItem,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/menu/items/bulk-price",
            json={"locationId": location.id, "changePct": 10},
            headers=headers,
        )
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "catalog.item_updated"
    assert payload["bulk"] is True
    assert payload["updated"] == 1

"""Integration tests for menu management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, User


@pytest.mark.asyncio
async def test_create_and_list_categories(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user

    # Create a location
    location = Location(business_id=business.id, name="Main Branch")
    db.add(location)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    # Create category
    resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": location.id, "name": "Pizza", "nameHe": "פיצה"},
        headers=headers,
    )
    assert resp.status_code == 201
    cat = resp.json()
    assert cat["name"] == "Pizza"
    assert cat["nameHe"] == "פיצה"

    # List categories
    resp = await client.get(f"/api/v1/menu/locations/{location.id}/categories", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_create_menu_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main Branch")
    db.add(location)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    # Create category first
    cat_resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": location.id, "name": "Pizza"},
        headers=headers,
    )
    category_id = cat_resp.json()["id"]

    # Create item
    resp = await client.post(
        "/api/v1/menu/items",
        json={
            "categoryId": category_id,
            "name": "Margherita",
            "nameHe": "מרגריטה",
            "price": 55.0,
            "taxRate": 0.17,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    assert item["name"] == "Margherita"
    assert item["price"] == 55.0


@pytest.mark.asyncio
async def test_bulk_price_update(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main Branch")
    db.add(location)
    await db.flush()

    headers = {"Authorization": f"Bearer {token}"}

    cat_resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": location.id, "name": "Drinks"},
        headers=headers,
    )
    category_id = cat_resp.json()["id"]

    for name, price in [("Coffee", 12.0), ("Tea", 10.0)]:
        await client.post(
            "/api/v1/menu/items",
            json={"categoryId": category_id, "name": name, "price": price},
            headers=headers,
        )

    # Increase prices by 10%
    resp = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id, "categoryId": category_id, "changePct": 10.0},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2

    # Verify prices updated
    items_resp = await client.get(f"/api/v1/menu/categories/{category_id}/items", headers=headers)
    items = items_resp.json()
    prices = {i["name"]: i["price"] for i in items}
    assert abs(prices["Coffee"] - 13.2) < 0.01
    assert abs(prices["Tea"] - 11.0) < 0.01


@pytest.mark.asyncio
async def test_delete_category_with_items_is_409(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main Branch")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}

    cat_resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": location.id, "name": "Pizza"},
        headers=headers,
    )
    category_id = cat_resp.json()["id"]
    await client.post(
        "/api/v1/menu/items",
        json={"categoryId": category_id, "name": "Margherita", "price": 55.0},
        headers=headers,
    )

    resp = await client.delete(f"/api/v1/menu/categories/{category_id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Category has items or subcategories"

    listed = await client.get(f"/api/v1/menu/locations/{location.id}/categories", headers=headers)
    assert any(row["id"] == category_id for row in listed.json())


@pytest.mark.asyncio
async def test_manager_required_for_mutation(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
):
    """Unauthenticated request should get 403."""
    resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": "any", "name": "Test"},
    )
    assert resp.status_code in (401, 403)  # missing/invalid token

"""Integration tests for menu item trash: move-to-trash (soft-delete), restore, and
permanent-delete, plus exclusion of trashed items from every default listing surface."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, User


async def _create_category_and_item(client: AsyncClient, headers: dict, location_id: str) -> tuple[str, str]:
    cat_resp = await client.post(
        "/api/v1/menu/categories",
        json={"locationId": location_id, "name": "Soups"},
        headers=headers,
    )
    category_id = cat_resp.json()["id"]
    item_resp = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": category_id, "name": "Tomato Soup", "price": 22.0},
        headers=headers,
    )
    return category_id, item_resp.json()["id"]


@pytest.mark.asyncio
async def test_delete_item_soft_deletes_and_excludes_from_list(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    category_id, item_id = await _create_category_and_item(client, headers, location.id)

    resp = await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)
    assert resp.status_code == 204

    # Excluded from the category item list (menu editor / order-taking grid data source)...
    resp = await client.get(f"/api/v1/menu/categories/{category_id}/items", headers=headers)
    assert resp.json() == []

    # ...and from the location-wide "all items" listing (used by AI dispatch / printer routing).
    resp = await client.get(f"/api/v1/menu/locations/{location.id}/stock", headers=headers)
    assert resp.json() == []

    # A direct GET by id no longer resolves either (matches "not found", the same as a hard delete).
    resp = await client.get(f"/api/v1/menu/items/{item_id}", headers=headers)
    assert resp.status_code == 404

    # But the row itself still exists — visible in the trash listing.
    resp = await client.get(f"/api/v1/menu/locations/{location.id}/trash", headers=headers)
    assert resp.status_code == 200
    trashed = resp.json()
    assert len(trashed) == 1
    assert trashed[0]["id"] == item_id
    assert trashed[0]["deletedAt"] is not None


@pytest.mark.asyncio
async def test_delete_already_trashed_item_404s(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    _, item_id = await _create_category_and_item(client, headers, location.id)

    assert (await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)).status_code == 204
    resp = await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_restore_item(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    category_id, item_id = await _create_category_and_item(client, headers, location.id)

    await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)

    resp = await client.post(f"/api/v1/menu/items/{item_id}/restore", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deletedAt"] is None

    # Back in the normal listing, gone from the trash listing.
    resp = await client.get(f"/api/v1/menu/categories/{category_id}/items", headers=headers)
    assert [i["id"] for i in resp.json()] == [item_id]
    resp = await client.get(f"/api/v1/menu/locations/{location.id}/trash", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_restore_non_trashed_item_400s(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    _, item_id = await _create_category_and_item(client, headers, location.id)

    resp = await client.post(f"/api/v1/menu/items/{item_id}/restore", headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_permanently_delete_item_requires_trash_first(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    _, item_id = await _create_category_and_item(client, headers, location.id)

    # Cannot permanently delete an active (never-trashed) item.
    resp = await client.delete(f"/api/v1/menu/items/{item_id}/permanent", headers=headers)
    assert resp.status_code == 400

    await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)  # move to trash first

    resp = await client.delete(f"/api/v1/menu/items/{item_id}/permanent", headers=headers)
    assert resp.status_code == 204

    # Really gone now — not even in the trash listing.
    resp = await client.get(f"/api/v1/menu/locations/{location.id}/trash", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_permanently_delete_item_cascades_modifier_groups(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    _, item_id = await _create_category_and_item(client, headers, location.id)
    group = await client.post(
        "/api/v1/menu/modifier-groups",
        json={"itemId": item_id, "name": "Size", "modifiers": [{"name": "Large", "priceDelta": 2}]},
        headers=headers,
    )
    assert group.status_code == 201
    group_id = group.json()["id"]

    assert (await client.delete(f"/api/v1/menu/items/{item_id}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/v1/menu/items/{item_id}/permanent", headers=headers)).status_code == 204

    leftover = await client.patch(
        f"/api/v1/menu/modifier-groups/{group_id}",
        json={"name": "gone"},
        headers=headers,
    )
    assert leftover.status_code == 404


@pytest.mark.asyncio
async def test_bulk_price_update_excludes_trashed_items(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = Location(business_id=business.id, name="Main")
    db.add(location)
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    category_id, trashed_item_id = await _create_category_and_item(client, headers, location.id)
    await client.delete(f"/api/v1/menu/items/{trashed_item_id}", headers=headers)

    active_item_resp = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": category_id, "name": "Fresh Soup", "price": 10.0},
        headers=headers,
    )
    active_item_id = active_item_resp.json()["id"]

    resp = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id, "categoryId": category_id, "changePct": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1  # only the active item, not the trashed one

    active_item = (await client.get(f"/api/v1/menu/items/{active_item_id}", headers=headers)).json()
    assert active_item["price"] == 11.0

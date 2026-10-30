"""Q8 catalog field bounds, parent cycles, reorder body, and bulk price clamp."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, User


async def _location(db: AsyncSession, business: Business) -> Location:
    location = Location(business_id=business.id, name="Main Branch")
    db.add(location)
    await db.flush()
    return location


@pytest.mark.asyncio
async def test_item_price_and_name_bounds(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = await _location(db, business)
    headers = {"Authorization": f"Bearer {token}"}
    cat = (
        await client.post(
            "/api/v1/menu/categories",
            json={"locationId": location.id, "name": "Mains"},
            headers=headers,
        )
    ).json()

    negative = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "Bad", "price": -1},
        headers=headers,
    )
    assert negative.status_code == 422

    blank = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "   ", "price": 10},
        headers=headers,
    )
    assert blank.status_code == 422

    too_long = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "x" * 256, "price": 10},
        headers=headers,
    )
    assert too_long.status_code == 422

    prep = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "Slow", "price": 10, "preparationTimeMin": 241},
        headers=headers,
    )
    assert prep.status_code == 422

    trimmed = await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "  Burger  ", "price": 0, "preparationTimeMin": 0},
        headers=headers,
    )
    assert trimmed.status_code == 201
    assert trimmed.json()["name"] == "Burger"
    assert trimmed.json()["price"] == 0


@pytest.mark.asyncio
async def test_modifier_delta_and_group_bounds(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = await _location(db, business)
    headers = {"Authorization": f"Bearer {token}"}
    cat = (
        await client.post(
            "/api/v1/menu/categories",
            json={"locationId": location.id, "name": "Mains"},
            headers=headers,
        )
    ).json()
    item = (
        await client.post(
            "/api/v1/menu/items",
            json={"categoryId": cat["id"], "name": "Burger", "price": 50},
            headers=headers,
        )
    ).json()

    required_no_min = await client.post(
        "/api/v1/menu/modifier-groups",
        json={"itemId": item["id"], "name": "Cheese", "required": True, "minSelect": 0, "maxSelect": 1},
        headers=headers,
    )
    assert required_no_min.status_code == 422

    inverted = await client.post(
        "/api/v1/menu/modifier-groups",
        json={"itemId": item["id"], "name": "Cheese", "minSelect": 2, "maxSelect": 1},
        headers=headers,
    )
    assert inverted.status_code == 422

    too_low = await client.post(
        "/api/v1/menu/modifier-groups",
        json={
            "itemId": item["id"],
            "name": "Extras",
            "modifiers": [{"name": "No cheese", "priceDelta": -1001}],
        },
        headers=headers,
    )
    assert too_low.status_code == 422

    ok = await client.post(
        "/api/v1/menu/modifier-groups",
        json={
            "itemId": item["id"],
            "name": "Extras",
            "required": True,
            "minSelect": 1,
            "maxSelect": 1,
            "modifiers": [{"name": "No cheese", "priceDelta": -2}],
        },
        headers=headers,
    )
    assert ok.status_code == 201
    assert ok.json()["modifiers"][0]["priceDelta"] == pytest.approx(-2)


@pytest.mark.asyncio
async def test_category_parent_cycle_and_move_to_root(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = await _location(db, business)
    headers = {"Authorization": f"Bearer {token}"}
    parent = (
        await client.post(
            "/api/v1/menu/categories",
            json={"locationId": location.id, "name": "Parent"},
            headers=headers,
        )
    ).json()
    child = (
        await client.post(
            "/api/v1/menu/categories",
            json={"locationId": location.id, "name": "Child", "parentId": parent["id"]},
            headers=headers,
        )
    ).json()

    self_parent = await client.patch(
        f"/api/v1/menu/categories/{parent['id']}",
        json={"parentId": parent["id"]},
        headers=headers,
    )
    assert self_parent.status_code == 400

    cycle = await client.patch(
        f"/api/v1/menu/categories/{parent['id']}",
        json={"parentId": child["id"]},
        headers=headers,
    )
    assert cycle.status_code == 400

    to_root = await client.patch(
        f"/api/v1/menu/categories/{child['id']}",
        json={"parentId": None},
        headers=headers,
    )
    assert to_root.status_code == 200
    assert to_root.json()["parentId"] is None


@pytest.mark.asyncio
async def test_reorder_requires_ids(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = await _location(db, business)
    headers = {"Authorization": f"Bearer {token}"}
    empty = await client.post(
        f"/api/v1/menu/locations/{location.id}/categories/reorder",
        json={},
        headers=headers,
    )
    assert empty.status_code == 422


@pytest.mark.asyncio
async def test_bulk_price_exactly_one_change_and_floor(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    location = await _location(db, business)
    headers = {"Authorization": f"Bearer {token}"}
    cat = (
        await client.post(
            "/api/v1/menu/categories",
            json={"locationId": location.id, "name": "Drinks"},
            headers=headers,
        )
    ).json()
    await client.post(
        "/api/v1/menu/items",
        json={"categoryId": cat["id"], "name": "Coffee", "price": 10},
        headers=headers,
    )

    both = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id, "changePct": 10, "changeAbs": 1},
        headers=headers,
    )
    assert both.status_code == 422

    neither = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id},
        headers=headers,
    )
    assert neither.status_code == 422

    pct_range = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id, "changePct": -91},
        headers=headers,
    )
    assert pct_range.status_code == 422

    floored = await client.post(
        "/api/v1/menu/items/bulk-price",
        json={"locationId": location.id, "categoryId": cat["id"], "changeAbs": -50},
        headers=headers,
    )
    assert floored.status_code == 200
    items = (await client.get(f"/api/v1/menu/categories/{cat['id']}/items", headers=headers)).json()
    assert items[0]["price"] == 0

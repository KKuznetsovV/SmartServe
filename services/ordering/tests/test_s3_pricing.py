"""Server-side modifier snapshots, qty/discount bounds, and group validation."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuItem, Modifier, ModifierGroup, User


async def _open_order(client: AsyncClient, token: str, location_id: str) -> str:
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location_id, "channel": "takeaway"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_client_price_delta_is_ignored(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
    location: Location,
):
    _, token = manager_user
    burger = MenuItem(category_id="cat-1", name="Burger", price=68.0, tax_rate=0.17)
    db.add(burger)
    await db.flush()
    group = ModifierGroup(item_id=burger.id, name="Doneness", required=False, min_select=0, max_select=1)
    db.add(group)
    await db.flush()
    modifier = Modifier(group_id=group.id, name="Medium", price_delta=0.0, active=True)
    db.add(modifier)
    await db.flush()

    order_id = await _open_order(client, token, location.id)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={
            "menuItemId": burger.id,
            "qty": 1,
            "modifiers": [{"modifierId": modifier.id, "name": "hack", "priceDelta": -68}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["unitPrice"] == pytest.approx(68.0)
    assert body["modifiers"][0]["name"] == "Medium"
    assert body["modifiers"][0]["priceDelta"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_qty_and_percent_discount_bounds(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
    location: Location,
    menu_item: MenuItem,
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order_id = await _open_order(client, token, location.id)

    negative_qty = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": -3},
        headers=headers,
    )
    assert negative_qty.status_code == 422

    too_many = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": 100},
        headers=headers,
    )
    assert too_many.status_code == 422

    line = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": 1},
        headers=headers,
    )
    assert line.status_code == 201
    item_id = line.json()["id"]

    negative_percent = await client.post(
        f"/api/v1/orders/{order_id}/items/discount",
        json={"items": [{"itemId": item_id}], "discountType": "percent", "discountValue": -50},
        headers=headers,
    )
    assert negative_percent.status_code == 422

    over_line = await client.post(
        f"/api/v1/orders/{order_id}/items/discount",
        json={"items": [{"itemId": item_id}], "discountType": "fixed", "discountValue": 999},
        headers=headers,
    )
    assert over_line.status_code == 422


@pytest.mark.asyncio
async def test_modifier_must_belong_to_item_and_required_group(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
    location: Location,
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    burger = MenuItem(category_id="cat-1", name="Burger", price=68.0)
    cola = MenuItem(category_id="cat-1", name="Cola", price=12.0)
    db.add_all([burger, cola])
    await db.flush()
    burger_group = ModifierGroup(item_id=burger.id, name="Doneness", required=False, min_select=0, max_select=1)
    required_group = ModifierGroup(item_id=cola.id, name="Size", required=True, min_select=1, max_select=1)
    db.add_all([burger_group, required_group])
    await db.flush()
    burger_mod = Modifier(group_id=burger_group.id, name="Medium", price_delta=0.0)
    cola_mod = Modifier(group_id=required_group.id, name="Large", price_delta=3.0)
    db.add_all([burger_mod, cola_mod])
    await db.flush()

    order_id = await _open_order(client, token, location.id)

    wrong_item = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": cola.id, "qty": 1, "modifiers": [{"modifierId": burger_mod.id}]},
        headers=headers,
    )
    assert wrong_item.status_code == 422

    missing = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": cola.id, "qty": 1, "modifiers": []},
        headers=headers,
    )
    assert missing.status_code == 422

    inactive = Modifier(group_id=required_group.id, name="Retired", price_delta=1.0, active=False)
    db.add(inactive)
    await db.flush()

    inactive_resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": cola.id, "qty": 1, "modifiers": [{"modifierId": inactive.id}]},
        headers=headers,
    )
    assert inactive_resp.status_code == 422

    ok = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": cola.id, "qty": 1, "modifiers": [{"modifierId": cola_mod.id}]},
        headers=headers,
    )
    assert ok.status_code == 201
    assert ok.json()["unitPrice"] == pytest.approx(15.0)

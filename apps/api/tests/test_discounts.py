"""Tests for discount creation and apply-to-order endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuItem, User


@pytest.mark.asyncio
async def test_create_and_list_discounts(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/discounts",
        json={"businessId": business.id, "code": "save10", "name": "10% Off", "type": "percent", "value": 10, "minOrderAmount": 0},
        headers=headers,
    )
    assert resp.status_code == 201
    d = resp.json()
    assert d["code"] == "SAVE10"
    assert d["type"] == "percent"
    assert d["value"] == 10
    assert d["active"] is True

    resp = await client.get(f"/api/v1/businesses/{business.id}/discounts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_discount_code_rejected(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"businessId": business.id, "code": "DUP", "name": "Dup", "type": "fixed", "value": 5, "minOrderAmount": 0}
    await client.post("/api/v1/discounts", json=payload, headers=headers)
    resp = await client.post("/api/v1/discounts", json=payload, headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_apply_discount_to_order(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Create a 20% discount
    await client.post(
        "/api/v1/discounts",
        json={"businessId": business.id, "code": "twenty", "name": "20% Off", "type": "percent", "value": 20, "minOrderAmount": 0},
        headers=headers,
    )

    # Create order with one item
    resp = await client.post(
        "/api/v1/orders", json={"locationId": location.id, "channel": "dine_in", "guestCount": 2}, headers=headers
    )
    order_id = resp.json()["id"]
    await client.post(f"/api/v1/orders/{order_id}/items", json={"menuItemId": menu_item.id, "qty": 1}, headers=headers)

    # Apply discount
    resp = await client.post(f"/api/v1/orders/{order_id}/discount", json={"code": "TWENTY"}, headers=headers)
    assert resp.status_code == 200
    order = resp.json()
    assert order["discountAmount"] > 0
    assert order["discountId"] is not None
    expected_discount = round(order["subtotal"] * 0.20, 2)
    assert abs(order["discountAmount"] - expected_discount) < 0.01
    assert order["total"] == pytest.approx(order["subtotal"] + order["taxAmount"] - order["discountAmount"], rel=1e-3)


@pytest.mark.asyncio
async def test_toggle_discount_active(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/discounts",
        json={"businessId": business.id, "code": "TOGGLE", "name": "Toggle", "type": "fixed", "value": 3, "minOrderAmount": 0},
        headers=headers,
    )
    discount_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/discounts/{discount_id}", json={"active": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["active"] is False

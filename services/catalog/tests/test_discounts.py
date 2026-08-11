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
        json={
            "businessId": business.id,
            "code": "save10",
            "name": "10% Off",
            "type": "percent",
            "value": 10,
            "minOrderAmount": 0,
        },
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
    payload = {
        "businessId": business.id,
        "code": "DUP",
        "name": "Dup",
        "type": "fixed",
        "value": 5,
        "minOrderAmount": 0,
    }
    await client.post("/api/v1/discounts", json=payload, headers=headers)
    resp = await client.post("/api/v1/discounts", json=payload, headers=headers)
    assert resp.status_code == 409


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
        json={
            "businessId": business.id,
            "code": "TOGGLE",
            "name": "Toggle",
            "type": "fixed",
            "value": 3,
            "minOrderAmount": 0,
        },
        headers=headers,
    )
    discount_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/discounts/{discount_id}", json={"active": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["active"] is False

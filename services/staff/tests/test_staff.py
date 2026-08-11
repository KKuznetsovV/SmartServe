"""Tests for staff CRUD endpoints (previously untested in apps/api — see docs/microservices-plan.md §4)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@pytest.mark.asyncio
async def test_create_staff(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/staff",
        json={"name": "New Waiter", "role": "waiter", "pin": "1234"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "New Waiter"
    assert body["role"] == "waiter"
    assert body["businessId"] == "biz-fixture"


@pytest.mark.asyncio
async def test_create_staff_rejects_duplicate_email(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/staff",
        json={"name": "Waiter One", "email": "dup@test.com", "role": "waiter"},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/staff",
        json={"name": "Waiter Two", "email": "dup@test.com", "role": "waiter"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_and_update_staff(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/staff",
        json={"name": "Kitchen Staffer", "role": "kitchen"},
        headers=headers,
    )
    user_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/staff/{user_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Kitchen Staffer"

    update_resp = await client.patch(
        f"/api/v1/staff/{user_id}",
        json={"role": "manager", "active": False},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["role"] == "manager"
    assert updated["active"] is False


@pytest.mark.asyncio
async def test_get_staff_not_found(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/staff/does-not-exist", headers=headers)
    assert resp.status_code == 404

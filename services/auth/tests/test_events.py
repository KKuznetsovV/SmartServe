"""Tests for staff.created/staff.updated outbox rows."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Outbox, User


@pytest.mark.asyncio
async def test_create_staff_enqueues_staff_created(
    client: AsyncClient,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/staff",
        json={"name": "Waiter Bob", "role": "waiter", "pin": "1234"},
        headers=headers,
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    db.expire_all()
    row = (await db.execute(select(Outbox))).scalar_one()
    payload = json.loads(row.payload)
    assert row.routing_key == "staff.created"
    assert payload["userId"] == user_id
    assert payload["role"] == "waiter"
    assert payload["businessId"] == business_id
    assert payload["eventId"]


@pytest.mark.asyncio
async def test_update_staff_enqueues_staff_updated(
    client: AsyncClient,
    manager_user: tuple[User, str],
    db: AsyncSession,
):
    user, token = manager_user
    business_id = user.business_id
    headers = {"Authorization": f"Bearer {token}"}

    created = (
        await client.post(
            "/api/v1/staff",
            json={"name": "Waiter Bob", "role": "waiter", "pin": "1234"},
            headers=headers,
        )
    ).json()

    resp = await client.patch(f"/api/v1/staff/{created['id']}", json={"name": "Robert"}, headers=headers)
    assert resp.status_code == 200

    db.expire_all()
    rows = (await db.execute(select(Outbox).where(Outbox.routing_key == "staff.updated"))).scalars().all()
    assert len(rows) == 1
    payload = json.loads(rows[0].payload)
    assert payload["userId"] == created["id"]
    assert payload["name"] == "Robert"
    assert payload["businessId"] == business_id

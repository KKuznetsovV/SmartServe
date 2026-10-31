"""PIN and password lockout (HTTP 423) against in-memory Redis."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_auth import _device_headers, _make_pin_user

from app.db.models import Business, Location, Outbox, User


@pytest.mark.asyncio
async def test_five_wrong_pins_lock_until_expiry(
    client: AsyncClient,
    db: AsyncSession,
    business: Business,
    location: Location,
    manager_user: tuple[User, str],
):
    user = await _make_pin_user(db, business.id, "1234", "Lockout Waiter")
    user_id = user.id
    business_id = business.id
    headers = await _device_headers(client, manager_user[1], location.id)
    body = {"locationId": location.id, "userId": user_id, "pin": "0000"}

    for i in range(4):
        resp = await client.post("/api/v1/auth/pin", json=body, headers=headers)
        assert resp.status_code == 401, i

    fifth = await client.post("/api/v1/auth/pin", json=body, headers=headers)
    assert fifth.status_code == 423
    assert int(fifth.headers["Retry-After"]) > 0

    correct = await client.post(
        "/api/v1/auth/pin",
        json={"locationId": location.id, "userId": user_id, "pin": "1234"},
        headers=headers,
    )
    assert correct.status_code == 423
    assert int(correct.headers["Retry-After"]) > 0

    db.expire_all()
    row = (await db.execute(select(Outbox).where(Outbox.routing_key == "auth.lockout"))).scalar_one()
    payload = json.loads(row.payload)
    assert payload["userId"] == user_id
    assert payload["businessId"] == business_id
    assert payload["deviceId"]


@pytest.mark.asyncio
async def test_password_login_lockout(client: AsyncClient, owner_user: tuple[User, str]):
    user, _ = owner_user
    body = {"email": user.email, "password": "wrong-password"}
    for _ in range(4):
        resp = await client.post("/api/v1/auth/login", json=body)
        assert resp.status_code == 401

    fifth = await client.post("/api/v1/auth/login", json=body)
    assert fifth.status_code == 423

    correct = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    assert correct.status_code == 423

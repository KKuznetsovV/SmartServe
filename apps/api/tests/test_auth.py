"""Tests for auth hardening: tenant-scoped PIN login and refresh claim preservation."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token, hash_password
from app.db.models import Business, Location, User


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _make_pin_user(db: AsyncSession, business_id: str, pin: str, name: str) -> User:
    user = User(business_id=business_id, name=name, role="waiter", pin_hash=hash_password(pin))
    db.add(user)
    await db.flush()
    return user


async def test_pin_login_scoped_to_business(
    client: AsyncClient, db: AsyncSession, business: Business, location: Location
):
    await _make_pin_user(db, business.id, "1234", "Waiter A")

    resp = await client.post("/api/v1/auth/pin", json={"locationId": location.id, "pin": "1234"})
    assert resp.status_code == 200
    payload = decode_token(resp.json()["accessToken"])
    assert payload["business_id"] == business.id


async def test_pin_login_rejects_other_business_pin(
    client: AsyncClient, db: AsyncSession, business: Business, location: Location
):
    other_biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(other_biz)
    await db.flush()
    await _make_pin_user(db, other_biz.id, "9999", "Other Waiter")

    # PIN belongs to a user of another business — must be rejected at this location
    resp = await client.post("/api/v1/auth/pin", json={"locationId": location.id, "pin": "9999"})
    assert resp.status_code == 401


async def test_pin_login_invalid_location(client: AsyncClient, db: AsyncSession, business: Business):
    await _make_pin_user(db, business.id, "1234", "Waiter A")
    resp = await client.post("/api/v1/auth/pin", json={"locationId": "nonexistent", "pin": "1234"})
    assert resp.status_code == 401


async def test_refresh_preserves_claims(client: AsyncClient, db: AsyncSession, owner_user: tuple[User, str]):
    user, _ = owner_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    assert login.status_code == 200
    refresh_token = login.json()["refreshToken"]

    resp = await client.post("/api/v1/auth/refresh", json={"refreshToken": refresh_token})
    assert resp.status_code == 200
    payload = decode_token(resp.json()["accessToken"])
    assert payload["business_id"] == user.business_id
    assert payload["role"] == user.role


async def test_refresh_rejects_deactivated_user(
    client: AsyncClient, db: AsyncSession, owner_user: tuple[User, str]
):
    user, _ = owner_user
    login = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password123"})
    refresh_token = login.json()["refreshToken"]

    user.active = False
    await db.flush()

    resp = await client.post("/api/v1/auth/refresh", json={"refreshToken": refresh_token})
    assert resp.status_code == 401

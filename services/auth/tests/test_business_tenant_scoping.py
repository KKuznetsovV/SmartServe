"""Cross-business authorization tests for business_router.py and location_router.py.

Every business_id/location_id-scoped endpoint here must 404 (never leak existence via 403)
when a caller from a DIFFERENT business tries to reach a resource that isn't theirs.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, User


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def other_business(db: AsyncSession) -> Business:
    biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(biz)
    await db.flush()
    return biz


@pytest_asyncio.fixture
async def other_owner(db: AsyncSession, other_business: Business) -> tuple[User, str]:
    user = User(
        business_id=other_business.id,
        email="other-owner@test.com",
        name="Other Owner",
        role="owner",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


async def test_get_business_rejects_other_business(
    client: AsyncClient, business: Business, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.get(f"/api/v1/businesses/{business.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_update_business_rejects_other_business(
    client: AsyncClient, business: Business, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.patch(
        f"/api/v1/businesses/{business.id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_list_locations_rejects_other_business(
    client: AsyncClient, business: Business, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.get(f"/api/v1/businesses/{business.id}/locations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_create_location_rejects_other_business(
    client: AsyncClient, business: Business, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.post(
        f"/api/v1/businesses/{business.id}/locations",
        json={"name": "New Branch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_list_staff_rejects_other_business(
    client: AsyncClient, business: Business, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.get(f"/api/v1/businesses/{business.id}/staff", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_get_location_rejects_other_business(
    client: AsyncClient, location: Location, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.get(f"/api/v1/locations/{location.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_update_location_rejects_other_business(
    client: AsyncClient, location: Location, other_owner: tuple[User, str]
):
    _, token = other_owner
    resp = await client.patch(
        f"/api/v1/locations/{location.id}",
        json={"name": "Hijacked Branch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

"""Cross-business authorization tests for cash-drawer shift endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@pytest_asyncio.fixture
async def other_manager(db: AsyncSession) -> tuple[User, str]:
    user = User(
        business_id="other-biz-fixture",
        email="other-manager@test.com",
        name="Other Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


@pytest.mark.asyncio
@pytest.mark.parametrize("path_suffix", ["", "/current", "/shifts/open"])
async def test_shift_location_routes_reject_other_business(
    client: AsyncClient,
    location_id: str,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str],
    path_suffix: str,
):
    _, other_token = other_manager
    headers = {"Authorization": f"Bearer {other_token}"}
    if path_suffix == "/shifts/open":
        resp = await client.post(
            f"/api/v1/locations/{location_id}/shifts/open",
            json={"openingCash": 0},
            headers=headers,
        )
    elif path_suffix == "/current":
        resp = await client.get(f"/api/v1/locations/{location_id}/shifts/current", headers=headers)
    else:
        resp = await client.get(f"/api/v1/locations/{location_id}/shifts", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_close_shift_rejects_other_business(
    client: AsyncClient,
    location_id: str,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str],
):
    _, owner_token = manager_user
    opened = await client.post(
        f"/api/v1/locations/{location_id}/shifts/open",
        json={"openingCash": 10},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert opened.status_code == 201
    _, other_token = other_manager
    resp = await client.post(
        f"/api/v1/shifts/{opened.json()['id']}/close",
        json={"closingCash": 10},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_open_shift_unknown_location_is_404(
    client: AsyncClient,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    resp = await client.post(
        "/api/v1/locations/missing/shifts/open",
        json={"openingCash": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

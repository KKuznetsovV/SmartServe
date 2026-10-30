"""Cross-business authorization tests for staff get/update endpoints.

A manager from a different business must never be able to reach or modify another
business's staff record via a guessed/known user_id path param.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, User


@pytest_asyncio.fixture
async def other_manager(db: AsyncSession) -> tuple[User, str]:
    other_biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(other_biz)
    await db.flush()
    user = User(
        business_id=other_biz.id,
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
async def test_get_staff_rejects_other_business(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str],
):
    _, owner_token = manager_user
    create_resp = await client.post(
        "/api/v1/staff",
        json={"name": "Waiter A", "role": "waiter"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    user_id = create_resp.json()["id"]

    _, other_token = other_manager
    resp = await client.get(f"/api/v1/staff/{user_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_staff_rejects_other_business(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str],
):
    _, owner_token = manager_user
    create_resp = await client.post(
        "/api/v1/staff",
        json={"name": "Waiter B", "role": "waiter"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    user_id = create_resp.json()["id"]

    _, other_token = other_manager
    resp = await client.patch(
        f"/api/v1/staff/{user_id}",
        json={"role": "manager"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404

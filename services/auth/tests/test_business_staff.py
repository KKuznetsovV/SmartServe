"""Tests for GET /businesses/{business_id}/staff scoping (used by services/ai's
staff.deactivate/reactivate intents to resolve a staff member by name/email)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Business, User


async def test_list_staff_scoped_to_own_business(
    client: AsyncClient, db: AsyncSession, owner_user: tuple[User, str]
):
    user, token = owner_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/api/v1/businesses/{user.business_id}/staff", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert any(u["id"] == user.id for u in body)


async def test_list_staff_rejects_other_business(
    client: AsyncClient, db: AsyncSession, owner_user: tuple[User, str]
):
    # A manager/owner from one business must never be able to list another business's
    # staff by guessing/knowing its business_id.
    _, token = owner_user
    headers = {"Authorization": f"Bearer {token}"}

    other_biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(other_biz)
    await db.flush()
    other_user = User(
        business_id=other_biz.id, name="Other Manager", role="manager", password_hash=hash_password("password123")
    )
    db.add(other_user)
    await db.flush()

    resp = await client.get(f"/api/v1/businesses/{other_biz.id}/staff", headers=headers)
    assert resp.status_code == 404

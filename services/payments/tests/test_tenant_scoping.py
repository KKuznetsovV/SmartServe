"""Cross-business authorization tests for payment endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from tests.conftest import create_order


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
@pytest.mark.parametrize(
    "action",
    ["create", "get", "list"],
)
async def test_payments_reject_other_business(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str],
    action: str,
):
    _, owner_token = manager_user
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    order = await create_order(db, total=100.0)
    created = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 40.0},
        headers=owner_headers,
    )
    assert created.status_code == 201
    payment_id = created.json()["id"]

    _, other_token = other_manager
    other_headers = {"Authorization": f"Bearer {other_token}"}
    if action == "create":
        resp = await client.post(
            "/api/v1/payments",
            json={"orderId": order.id, "method": "cash", "amount": 10.0},
            headers=other_headers,
        )
    elif action == "get":
        resp = await client.get(f"/api/v1/payments/{payment_id}", headers=other_headers)
    else:
        resp = await client.get(f"/api/v1/orders/{order.id}/payments", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_payments_unknown_order_is_404(
    client: AsyncClient,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": "missing", "method": "cash", "amount": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

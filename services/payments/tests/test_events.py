"""Tests for the payment.completed publish call site (mocked mq.publish, no live broker)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from tests.conftest import create_order


@pytest.mark.asyncio
async def test_full_payment_publishes_payment_completed(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=100.0)

    with patch("smartserve_shared.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/payments",
            json={"orderId": order.id, "method": "cash", "amount": order.total},
            headers=headers,
        )
    assert resp.status_code == 201
    payment_id = resp.json()["id"]

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "payment.completed"
    assert payload["orderId"] == order.id
    assert payload["paymentId"] == payment_id
    assert payload["businessId"] == user.business_id


@pytest.mark.asyncio
async def test_partial_payment_does_not_publish_payment_completed(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=100.0)

    with patch("smartserve_shared.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/payments",
            json={"orderId": order.id, "method": "cash", "amount": 50.0},
            headers=headers,
        )
    assert resp.status_code == 201

    mock_publish.assert_not_awaited()

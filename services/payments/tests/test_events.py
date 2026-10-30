"""Tests for the payment.completed outbox row (no live broker)."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Outbox, User
from tests.conftest import create_order


@pytest.mark.asyncio
async def test_full_payment_enqueues_payment_completed(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    business_id = user.business_id
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=100.0)
    order_id = order.id
    order_total = order.total

    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order_id, "method": "cash", "amount": order_total},
        headers=headers,
    )
    assert resp.status_code == 201
    payment_id = resp.json()["id"]

    db.expire_all()
    row = (await db.execute(select(Outbox))).scalar_one()
    payload = json.loads(row.payload)
    assert row.routing_key == "payment.completed"
    assert payload["orderId"] == order_id
    assert payload["paymentId"] == payment_id
    assert payload["businessId"] == business_id
    assert payload["eventId"]


@pytest.mark.asyncio
async def test_partial_payment_does_not_enqueue_payment_completed(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=100.0)

    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 50.0},
        headers=headers,
    )
    assert resp.status_code == 201

    db.expire_all()
    rows = (await db.execute(select(Outbox))).scalars().all()
    assert rows == []

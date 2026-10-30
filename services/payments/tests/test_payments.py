"""Tests for payment creation and order status transition."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from tests.conftest import create_order


@pytest.mark.asyncio
async def test_payment_marks_order_paid(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)

    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": order.total},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["orderFullyPaid"] is True
    assert body["remaining"] == pytest.approx(0)

    await db.refresh(order)
    assert order.status == "submitted"


@pytest.mark.asyncio
async def test_list_order_payments(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)

    # Partial payment first
    await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": 50.0},
        headers=headers,
    )

    resp = await client.get(f"/api/v1/orders/{order.id}/payments", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["method"] == "card"


@pytest.mark.asyncio
async def test_split_payment_across_installments_marks_paid_once_fully_covered(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    """Regression test: previously a single payment's amount was compared against the
    full order total, so an order paid via several partial/split payments never
    transitioned to 'paid' even once fully covered."""
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)
    half = 50.0

    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": half, "guestNumber": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["orderFullyPaid"] is False
    assert resp.json()["remaining"] == pytest.approx(half)
    await db.refresh(order)
    assert order.status == "submitted"

    resp = await client.post(
        "/api/v1/payments",
        json={
            "orderId": order.id,
            "method": "card",
            "amount": order.total - half,
            "guestNumber": 2,
            "tipAmount": 5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipAmount"] == pytest.approx(5)
    assert body["guestNumber"] == 2

    await db.refresh(order)
    assert order.status == "submitted"
    assert body["orderFullyPaid"] is True
    assert body["remaining"] == pytest.approx(0)


@pytest.mark.asyncio
async def test_get_payment(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)
    create_resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 100.0},
        headers=headers,
    )
    payment_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/payments/{payment_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == payment_id


@pytest.mark.asyncio
async def test_create_payment_rejects_invalid_method(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "bitcoin", "amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_payment_rejects_already_paid_order(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_order(db, total=100.0)
    first = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 100.0},
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["orderFullyPaid"] is True
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 400

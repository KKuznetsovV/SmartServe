"""Tests for payment creation and order status transition."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from smartserve_shared.security import hash_password

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
    half = 50

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
            "amount": str(order.total - half),
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
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_exact_total_pays_in_full_one_cent_short_leaves_remaining(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total="10.10")

    short = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": "10.09"},
        headers=headers,
    )
    assert short.status_code == 201
    assert short.json()["orderFullyPaid"] is False
    assert short.json()["remaining"] == 0.01

    done = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": "0.01"},
        headers=headers,
    )
    assert done.status_code == 201
    assert done.json()["orderFullyPaid"] is True
    assert done.json()["remaining"] == 0


@pytest.mark.asyncio
async def test_cash_overpay_returns_change_due(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=68.0)
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == pytest.approx(68)
    assert body["tendered"] == pytest.approx(100)
    assert body["changeDue"] == pytest.approx(32)
    assert body["orderFullyPaid"] is True


@pytest.mark.asyncio
async def test_card_over_remaining_is_conflict(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=14.0)
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": 5000},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancelled_and_empty_orders_are_conflict(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    cancelled = await create_order(db, total=10.0, status="cancelled")
    pay_cancelled = await client.post(
        "/api/v1/payments",
        json={"orderId": cancelled.id, "method": "cash", "amount": 1},
        headers=headers,
    )
    assert pay_cancelled.status_code == 409

    empty = await create_order(db, total=0, status="submitted")
    pay_empty = await client.post(
        "/api/v1/payments",
        json={"orderId": empty.id, "method": "cash", "amount": 1},
        headers=headers,
    )
    assert pay_empty.status_code == 409


@pytest.mark.asyncio
async def test_idempotency_key_replays_original_payment(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "pay-once"}
    order = await create_order(db, total=20.0)
    first = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": 20.0},
        headers=headers,
    )
    second = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": 20.0},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    listed = await client.get(f"/api/v1/orders/{order.id}/payments", headers={"Authorization": f"Bearer {token}"})
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_refund_records_negative_row(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    user, token = manager_user
    user.pin_hash = hash_password("2222")
    await db.flush()
    headers = {"Authorization": f"Bearer {token}"}
    order = await create_order(db, total=40.0)
    created = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": 40.0},
        headers=headers,
    )
    payment_id = created.json()["id"]
    refunded = await client.post(
        f"/api/v1/payments/{payment_id}/refund",
        json={"managerUserId": user.id, "pin": "2222", "reason": "guest walked out"},
        headers=headers,
    )
    assert refunded.status_code == 200
    assert refunded.json()["amount"] == pytest.approx(-40)
    listed = await client.get(f"/api/v1/orders/{order.id}/payments", headers=headers)
    amounts = sorted(row["amount"] for row in listed.json())
    assert amounts == pytest.approx([-40, 40])

"""Tests for payment creation and order status transition."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuItem, User
from tests.conftest import create_submitted_order


@pytest.mark.asyncio
async def test_payment_marks_order_paid(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_submitted_order(db, location, [(menu_item, 1)])
    total = order.total
    assert total > 0

    # Pay full amount
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": total},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"

    # Order should now be paid
    await db.refresh(order)
    assert order.status == "paid"


@pytest.mark.asyncio
async def test_list_order_payments(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_submitted_order(db, location, [(menu_item, 2)], channel="takeaway", guest_count=None)
    total = order.total

    # Partial payment first
    await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "card", "amount": round(total / 2, 2)},
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
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    """Regression test: previously a single payment's amount was compared against the
    full order total, so an order paid via several partial/split payments never
    transitioned to 'paid' even once fully covered."""
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_submitted_order(db, location, [(menu_item, 2)])
    total = order.total
    half = round(total / 2, 2)

    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order.id, "method": "cash", "amount": half, "guestNumber": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    await db.refresh(order)
    assert order.status != "paid"

    resp = await client.post(
        "/api/v1/payments",
        json={
            "orderId": order.id,
            "method": "card",
            "amount": round(total - half, 2),
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
    assert order.status == "paid"

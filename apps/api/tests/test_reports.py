"""Tests for the reports summary endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuItem, User


@pytest.mark.asyncio
async def test_report_summary_empty(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        f"/api/v1/locations/{location.id}/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalRevenue"] == 0
    assert data["orderCount"] == 0
    assert data["avgOrderValue"] == 0
    assert data["topItems"] == []


@pytest.mark.asyncio
async def test_report_summary_with_paid_order(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    menu_item: MenuItem,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Create, submit, and pay an order
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers=headers,
    )
    order_id = resp.json()["id"]
    await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menuItemId": menu_item.id, "qty": 2},
        headers=headers,
    )
    await client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    total = (await client.get(f"/api/v1/orders/{order_id}", headers=headers)).json()["total"]
    await client.post(
        "/api/v1/payments",
        json={"orderId": order_id, "method": "cash", "amount": total},
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/locations/{location.id}/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["orderCount"] == 1
    assert data["totalRevenue"] == pytest.approx(total, rel=1e-3)
    assert data["avgOrderValue"] == pytest.approx(total, rel=1e-3)
    assert len(data["topItems"]) == 1
    assert data["topItems"][0]["menuItemName"] == "Burger"
    assert data["topItems"][0]["qty"] == 2
    assert "dine_in" in data["revenueByChannel"]

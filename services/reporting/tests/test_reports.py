"""Tests for the reports summary endpoint."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from tests.conftest import create_paid_order


@pytest.mark.asyncio
async def test_report_summary_empty(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/summary?period=today",
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
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    order = await create_paid_order(db, location_id, [("Burger", 2, 50.0)])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["orderCount"] == 1
    assert data["totalRevenue"] == pytest.approx(order.total, rel=1e-3)
    assert data["avgOrderValue"] == pytest.approx(order.total, rel=1e-3)
    assert len(data["topItems"]) == 1
    assert data["topItems"][0]["menuItemName"] == "Burger"
    assert data["topItems"][0]["qty"] == 2
    assert "dine_in" in data["revenueByChannel"]


@pytest.mark.asyncio
async def test_report_summary_requires_auth(client: AsyncClient, db: AsyncSession, location_id: str):
    resp = await client.get(f"/api/v1/locations/{location_id}/reports/summary?period=today")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_report_summary_excludes_other_locations(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    await create_paid_order(db, "other-location", [("Fries", 1, 20.0)])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["orderCount"] == 0

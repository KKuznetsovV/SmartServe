"""Tests for the reports summary endpoint."""

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, User
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
    assert data["vatCollected"] == 0
    assert data["netRevenue"] == 0
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
    assert data["vatCollected"] == pytest.approx(order.tax_amount, rel=1e-3)
    assert data["netRevenue"] == pytest.approx(order.total - order.tax_amount, rel=1e-3)
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


def _date_range() -> tuple[str, str]:
    now = datetime.now(UTC)
    start = quote((now - timedelta(days=1)).isoformat())
    end = quote((now + timedelta(days=1)).isoformat())
    return start, end


@pytest.mark.asyncio
async def test_report_summary_unknown_location_is_404(
    client: AsyncClient, db: AsyncSession, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(
        "/api/v1/locations/does-not-exist/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_summary_rejects_other_businesses_location(
    client: AsyncClient, db: AsyncSession, manager_user: tuple[User, str]
):
    other_location = Location(id="loc-other-biz", business_id="biz-someone-else", name="Someone Else's")
    db.add(other_location)
    await db.flush()

    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(
        "/api/v1/locations/loc-other-biz/reports/summary?period=today",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sales_report_grouped_by_item(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(
        db,
        location_id,
        [("Burger", 2, 50.0), ("Fries", 1, 20.0)],
        item_meta=[("item-1", "cat-1", "Mains"), ("item-2", "cat-2", "Sides")],
    )

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/sales?group_by=item&start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalQty"] == 3
    labels = {row["groupLabel"] for row in data["rows"]}
    assert labels == {"Burger", "Fries"}


@pytest.mark.asyncio
async def test_sales_report_grouped_by_category(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(
        db,
        location_id,
        [("Burger", 2, 50.0), ("Cheeseburger", 1, 60.0)],
        item_meta=[("item-1", "cat-1", "Mains"), ("item-3", "cat-1", "Mains")],
    )

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/sales?group_by=category&start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["groupLabel"] == "Mains"
    assert data["rows"][0]["qty"] == 3


@pytest.mark.asyncio
async def test_sales_report_grouped_by_menu(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(db, location_id, [("Burger", 2, 50.0)])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/sales?group_by=menu&start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalRevenue"] == pytest.approx(100.0)
    assert data["rows"][0]["groupLabel"] == "Whole menu"


@pytest.mark.asyncio
async def test_sales_by_server_report(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    user, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(db, location_id, [("Burger", 2, 50.0)], created_by=user.id)

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/sales-by-server?start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["serverId"] == user.id
    assert data["rows"][0]["serverName"] == user.name
    assert data["rows"][0]["orderCount"] == 1
    assert data["rows"][0]["revenue"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_sales_by_server_report_filtered_by_item(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    user, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(
        db,
        location_id,
        [("Burger", 2, 50.0), ("Fries", 1, 20.0)],
        created_by=user.id,
        item_meta=[("item-1", "cat-1", "Mains"), ("item-2", "cat-2", "Sides")],
    )

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/sales-by-server?start={start}&end={end}&item_id=item-1",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rows"][0]["qty"] == 2
    assert data["rows"][0]["revenue"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_closed_orders_report_filters_by_status(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(db, location_id, [("Burger", 1, 50.0)], status="paid")
    await create_paid_order(db, location_id, [("Fries", 1, 20.0)], status="cancelled")

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/closed-orders?start={start}&end={end}&status=paid",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["orders"]) == 1
    assert data["orders"][0]["status"] == "paid"

    resp_all = await client.get(
        f"/api/v1/locations/{location_id}/reports/closed-orders?start={start}&end={end}",
        headers=headers,
    )
    assert len(resp_all.json()["orders"]) == 2

    resp_other = await client.get(
        f"/api/v1/locations/{location_id}/reports/closed-orders?start={start}&end={end}&status=other",
        headers=headers,
    )
    assert resp_other.json()["orders"] == []


@pytest.mark.asyncio
async def test_export_sales_report_csv(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    await create_paid_order(db, location_id, [("Burger", 2, 50.0)])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/export?report_type=sales&group_by=item&start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text
    assert body.splitlines()[0] == "group_id,group_label,qty,revenue"
    assert "Burger" in body


@pytest.mark.asyncio
async def test_export_closed_orders_csv(
    client: AsyncClient, db: AsyncSession, location_id: str, manager_user: tuple[User, str]
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    start, end = _date_range()

    order = await create_paid_order(db, location_id, [("Burger", 1, 50.0)])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/export?report_type=closed-orders&start={start}&end={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.splitlines()
    assert lines[0] == "order_id,status,channel,total,created_by,created_by_name,created_at"
    assert order.id in lines[1]


@pytest.mark.asyncio
async def test_revenue_sum_has_no_float_drift(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(100):
        await create_paid_order(db, location_id, [("Widget", 1, "10.10")])

    resp = await client.get(
        f"/api/v1/locations/{location_id}/reports/summary?period=month",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["totalRevenue"] == 1010.0
    assert resp.json()["orderCount"] == 100

"""Tests for table management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, User


@pytest.mark.asyncio
async def test_table_crud(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    resp = await client.post(
        "/api/v1/tables",
        json={"locationId": location.id, "name": "T1", "capacity": 4},
        headers=headers,
    )
    assert resp.status_code == 201
    table_id = resp.json()["id"]
    assert resp.json()["name"] == "T1"
    assert resp.json()["capacity"] == 4

    # List
    resp = await client.get(f"/api/v1/locations/{location.id}/tables", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    status_resp = await client.get(
        f"/api/v1/locations/{location.id}/tables?include=status",
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()[0]["floorState"] == "free"
    assert status_resp.json()[0]["openOrder"] is None

    # Update
    resp = await client.patch(
        f"/api/v1/tables/{table_id}",
        json={"name": "T1-VIP", "capacity": 6},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "T1-VIP"
    assert resp.json()["capacity"] == 6

    # Delete
    resp = await client.delete(f"/api/v1/tables/{table_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/locations/{location.id}/tables", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_tables_include_status_attaches_open_order(
    client: AsyncClient,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    table_id = (
        await client.post(
            "/api/v1/tables",
            json={"locationId": location.id, "name": "T-live", "capacity": 2},
            headers=headers,
        )
    ).json()["id"]
    order = (
        await client.post(
            "/api/v1/orders",
            json={"locationId": location.id, "tableId": table_id, "channel": "dine_in", "guestCount": 2},
            headers=headers,
        )
    ).json()
    resp = await client.get(
        f"/api/v1/locations/{location.id}/tables?include=status",
        headers=headers,
    )
    assert resp.status_code == 200
    card = next(row for row in resp.json() if row["id"] == table_id)
    assert card["floorState"] == "seated"
    assert card["openOrder"]["id"] == order["id"]
    assert card["openOrder"]["status"] == "open"
    assert card["openOrder"]["guestCount"] == 2

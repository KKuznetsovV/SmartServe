"""Tests for shift open/close lifecycle."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, User


@pytest.mark.asyncio
async def test_open_and_close_shift(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    # Open shift
    resp = await client.post(
        f"/api/v1/locations/{location.id}/shifts/open",
        json={"openingCash": 500.0},
        headers=headers,
    )
    assert resp.status_code == 201
    shift = resp.json()
    assert shift["status"] == "open"
    assert shift["openingCash"] == 500.0
    assert shift["closedAt"] is None

    shift_id = shift["id"]

    # Current shift returns the open one
    resp = await client.get(f"/api/v1/locations/{location.id}/shifts/current", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == shift_id

    # Close shift
    resp = await client.post(
        f"/api/v1/shifts/{shift_id}/close",
        json={"closingCash": 520.0},
        headers=headers,
    )
    assert resp.status_code == 200
    closed = resp.json()
    assert closed["status"] == "closed"
    assert closed["closingCash"] == 520.0
    assert closed["closedAt"] is not None

    # Current shift is now None
    resp = await client.get(f"/api/v1/locations/{location.id}/shifts/current", headers=headers)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_duplicate_open_rejected(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        f"/api/v1/locations/{location.id}/shifts/open",
        json={"openingCash": 100.0},
        headers=headers,
    )

    resp = await client.post(
        f"/api/v1/locations/{location.id}/shifts/open",
        json={"openingCash": 200.0},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_shifts(
    client: AsyncClient,
    db: AsyncSession,
    location: Location,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"/api/v1/locations/{location.id}/shifts/open",
        json={"openingCash": 0.0},
        headers=headers,
    )
    shift_id = resp.json()["id"]
    await client.post(f"/api/v1/shifts/{shift_id}/close", json={"closingCash": 0.0}, headers=headers)

    resp = await client.get(f"/api/v1/locations/{location.id}/shifts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

"""Tests for printer CRUD (previously untested in apps/api — see docs/microservices-plan.md §4)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@pytest.mark.asyncio
async def test_create_and_list_printers(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Kitchen Printer", "type": "kitchen"},
        headers=headers,
    )
    assert resp.status_code == 201
    printer = resp.json()
    assert printer["name"] == "Kitchen Printer"
    assert printer["type"] == "kitchen"
    assert printer["active"] is True

    resp = await client.get(f"/api/v1/locations/{location_id}/printers", headers=headers)
    assert resp.status_code == 200
    printers = resp.json()
    assert len(printers) == 1
    assert printers[0]["id"] == printer["id"]


@pytest.mark.asyncio
async def test_update_printer(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Receipt Printer"},
        headers=headers,
    )
    printer_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/printers/{printer_id}",
        json={"active": False, "ip": "192.168.1.50"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["active"] is False
    assert updated["ip"] == "192.168.1.50"


@pytest.mark.asyncio
async def test_delete_printer(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Label Printer", "type": "label"},
        headers=headers,
    )
    printer_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/printers/{printer_id}", headers=headers)
    assert delete_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/locations/{location_id}/printers", headers=headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_update_nonexistent_printer_404(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch("/api/v1/printers/does-not-exist", json={"active": False}, headers=headers)
    assert resp.status_code == 404

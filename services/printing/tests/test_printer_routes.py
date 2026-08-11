"""Tests for printer-route assignment (item -> printer fan-out for KDS/receipt routing)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def _create_printer(client: AsyncClient, headers: dict, location_id: str) -> str:
    resp = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Kitchen Printer", "type": "kitchen"},
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_add_and_list_routes(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    printer_id = await _create_printer(client, headers, location_id)

    resp = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": "item-1"},
        headers=headers,
    )
    assert resp.status_code == 201
    route = resp.json()
    assert route["printerId"] == printer_id
    assert route["itemId"] == "item-1"

    resp = await client.get(f"/api/v1/locations/{location_id}/printer-routes", headers=headers)
    assert resp.status_code == 200
    routes = resp.json()
    assert len(routes) == 1
    assert routes[0]["itemId"] == "item-1"


@pytest.mark.asyncio
async def test_add_route_is_idempotent(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    printer_id = await _create_printer(client, headers, location_id)

    first = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": "item-1"},
        headers=headers,
    )
    second = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": "item-1"},
        headers=headers,
    )
    assert first.json()["id"] == second.json()["id"]

    resp = await client.get(f"/api/v1/locations/{location_id}/printer-routes", headers=headers)
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_delete_route(
    client: AsyncClient,
    db: AsyncSession,
    location_id: str,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}
    printer_id = await _create_printer(client, headers, location_id)

    create_resp = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": "item-1"},
        headers=headers,
    )
    route_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/printer-routes/{route_id}", headers=headers)
    assert delete_resp.status_code == 204

    resp = await client.get(f"/api/v1/locations/{location_id}/printer-routes", headers=headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_route_404(
    client: AsyncClient,
    db: AsyncSession,
    manager_user: tuple[User, str],
):
    _, token = manager_user
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.delete("/api/v1/printer-routes/does-not-exist", headers=headers)
    assert resp.status_code == 404

"""Cross-business authorization tests for printer and route endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuCategory, MenuItem, User


@pytest_asyncio.fixture
async def other_manager(db: AsyncSession) -> tuple[User, str, str, str]:
    user = User(
        business_id="other-biz-fixture",
        email="other-manager@test.com",
        name="Other Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    location = Location(business_id="other-biz-fixture", name="Other")
    db.add_all([user, location])
    await db.flush()
    category = MenuCategory(location_id=location.id)
    db.add(category)
    await db.flush()
    item = MenuItem(category_id=category.id)
    db.add(item)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token, location.id, item.id


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["list_printers", "list_jobs", "list_routes", "create"])
async def test_printer_location_routes_reject_other_business(
    client: AsyncClient,
    location_id: str,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str, str, str],
    kind: str,
):
    _, other_token, _, _ = other_manager
    headers = {"Authorization": f"Bearer {other_token}"}
    if kind == "create":
        resp = await client.post(
            "/api/v1/printers",
            json={"locationId": location_id, "name": "B on A", "type": "kitchen"},
            headers=headers,
        )
    elif kind == "list_jobs":
        resp = await client.get(f"/api/v1/locations/{location_id}/print-jobs", headers=headers)
    elif kind == "list_routes":
        resp = await client.get(f"/api/v1/locations/{location_id}/printer-routes", headers=headers)
    else:
        resp = await client.get(f"/api/v1/locations/{location_id}/printers", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_printer_and_route_mutations_reject_other_business(
    client: AsyncClient,
    location_id: str,
    menu_item_id: str,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str, str, str],
):
    _, owner_token = manager_user
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    printer = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Kitchen", "type": "kitchen"},
        headers=owner_headers,
    )
    assert printer.status_code == 201
    printer_id = printer.json()["id"]
    route = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": menu_item_id},
        headers=owner_headers,
    )
    assert route.status_code == 201

    _, other_token, _, other_item_id = other_manager
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert (
        await client.patch(
            f"/api/v1/printers/{printer_id}",
            json={"active": False},
            headers=other_headers,
        )
    ).status_code == 404
    assert (await client.delete(f"/api/v1/printers/{printer_id}", headers=other_headers)).status_code == 404
    assert (
        await client.post(
            "/api/v1/printer-routes",
            json={"printerId": printer_id, "itemId": other_item_id},
            headers=other_headers,
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/printer-routes/{route.json()['id']}", headers=other_headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_route_rejects_item_from_other_business(
    client: AsyncClient,
    location_id: str,
    manager_user: tuple[User, str],
    other_manager: tuple[User, str, str, str],
):
    _, owner_token = manager_user
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    printer = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Kitchen", "type": "kitchen"},
        headers=owner_headers,
    )
    _, _, _, other_item_id = other_manager
    resp = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer.json()["id"], "itemId": other_item_id},
        headers=owner_headers,
    )
    assert resp.status_code == 404

"""Cross-business authorization tests for ordering endpoints (orders and tables).

A user from a DIFFERENT business must never be able to reach or modify another
business's orders, order items, or tables via a guessed/known id path param.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location, MenuItem, Order, Table, User


@pytest_asyncio.fixture
async def other_business(db: AsyncSession) -> Business:
    biz = Business(name="Other Restaurant", country="IL", currency="ILS")
    db.add(biz)
    await db.flush()
    return biz


@pytest_asyncio.fixture
async def other_manager(db: AsyncSession, other_business: Business) -> tuple[User, str]:
    user = User(
        business_id=other_business.id,
        email="other-manager@test.com",
        name="Other Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


@pytest_asyncio.fixture
async def order(db: AsyncSession, location: Location) -> Order:
    o = Order(location_id=location.id, channel="dine_in", status="open", guest_count=2)
    db.add(o)
    await db.flush()
    return o


@pytest_asyncio.fixture
async def table(db: AsyncSession, location: Location) -> Table:
    t = Table(location_id=location.id, name="1", capacity=4)
    db.add(t)
    await db.flush()
    return t


@pytest.mark.asyncio
async def test_get_order_rejects_other_business(client: AsyncClient, order: Order, other_manager: tuple[User, str]):
    _, token = other_manager
    resp = await client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_orders_rejects_other_business(
    client: AsyncClient, location: Location, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.get(f"/api/v1/locations/{location.id}/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_order_rejects_other_business_location(
    client: AsyncClient, location: Location, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.post(
        "/api/v1/orders",
        json={"locationId": location.id, "channel": "dine_in", "guestCount": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_order_item_rejects_other_business(
    client: AsyncClient, order: Order, menu_item: MenuItem, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.post(
        f"/api/v1/orders/{order.id}/items",
        json={"menuItemId": menu_item.id, "qty": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_order_rejects_other_business(client: AsyncClient, order: Order, other_manager: tuple[User, str]):
    _, token = other_manager
    resp = await client.post(f"/api/v1/orders/{order.id}/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_order_rejects_other_business(client: AsyncClient, order: Order, other_manager: tuple[User, str]):
    _, token = other_manager
    resp = await client.post(f"/api/v1/orders/{order.id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_tables_rejects_other_business(
    client: AsyncClient, location: Location, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.get(f"/api/v1/locations/{location.id}/tables", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_table_rejects_other_business_location(
    client: AsyncClient, location: Location, other_manager: tuple[User, str]
):
    _, token = other_manager
    resp = await client.post(
        "/api/v1/tables",
        json={"locationId": location.id, "name": "5", "capacity": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_table_rejects_other_business(client: AsyncClient, table: Table, other_manager: tuple[User, str]):
    _, token = other_manager
    resp = await client.patch(
        f"/api/v1/tables/{table.id}",
        json={"capacity": 8},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_table_rejects_other_business(client: AsyncClient, table: Table, other_manager: tuple[User, str]):
    _, token = other_manager
    resp = await client.delete(f"/api/v1/tables/{table.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404

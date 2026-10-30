"""Regression test for the get_db() commit bug.

Unlike the shared-session `db`/`client` fixtures in conftest.py (which reuse one open
AsyncSession for the whole test and would mask a missing commit()), this test exercises
the real `app.db.session.get_db` so each request gets its own session, then reads back
through a fresh session after the request completes.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.session as session_module
from app.db.models import Location, MenuCategory, MenuItem, Printer, PrinterRoute, User
from app.db.session import Base
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def fresh_session_client(monkeypatch):
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _manager_setup(session_factory) -> tuple[dict[str, str], str, str]:
    async with session_factory() as setup_session:
        user = User(
            business_id="biz-fixture",
            email="manager@test.com",
            name="Manager",
            role="manager",
            password_hash=hash_password("password123"),
        )
        location = Location(business_id="biz-fixture", name="Main")
        setup_session.add_all([user, location])
        await setup_session.flush()
        category = MenuCategory(location_id=location.id)
        setup_session.add(category)
        await setup_session.flush()
        item = MenuItem(category_id=category.id)
        setup_session.add(item)
        await setup_session.commit()
        token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
        return {"Authorization": f"Bearer {token}"}, location.id, item.id


@pytest.mark.asyncio
async def test_created_printer_and_route_persist_across_fresh_sessions(fresh_session_client):
    client, session_factory = fresh_session_client
    headers, location_id, item_id = await _manager_setup(session_factory)

    resp = await client.post(
        "/api/v1/printers",
        json={"locationId": location_id, "name": "Kitchen Printer", "type": "kitchen"},
        headers=headers,
    )
    assert resp.status_code == 201
    printer_id = resp.json()["id"]

    async with session_factory() as verify_session:
        printer = (await verify_session.execute(select(Printer).where(Printer.id == printer_id))).scalar_one()
        assert printer.name == "Kitchen Printer"
        assert printer.type == "kitchen"

    route_resp = await client.post(
        "/api/v1/printer-routes",
        json={"printerId": printer_id, "itemId": item_id},
        headers=headers,
    )
    assert route_resp.status_code == 201
    route_id = route_resp.json()["id"]

    async with session_factory() as verify_session:
        route = (await verify_session.execute(select(PrinterRoute).where(PrinterRoute.id == route_id))).scalar_one()
        assert route.printer_id == printer_id
        assert route.item_id == item_id

    list_resp = await client.get(f"/api/v1/locations/{location_id}/printers", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["id"] == printer_id

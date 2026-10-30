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
from app.db.models import Location, Shift, User
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


async def _manager_headers(session_factory) -> tuple[dict[str, str], str]:
    async with session_factory() as setup_session:
        user = User(
            business_id="biz-fixture",
            email="manager@test.com",
            name="Manager",
            role="manager",
            password_hash=hash_password("password123"),
        )
        setup_session.add(user)
        location = Location(business_id="biz-fixture", name="Main")
        setup_session.add(location)
        await setup_session.commit()
        token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
        return {"Authorization": f"Bearer {token}"}, user.id, location.id


@pytest.mark.asyncio
async def test_created_staff_persists_across_fresh_sessions(fresh_session_client):
    client, session_factory = fresh_session_client
    headers, *_ = await _manager_headers(session_factory)

    resp = await client.post(
        "/api/v1/staff",
        json={"name": "New Waiter", "role": "waiter", "pin": "1234"},
        headers=headers,
    )
    assert resp.status_code == 201
    staff_id = resp.json()["id"]

    async with session_factory() as verify_session:
        staff = (await verify_session.execute(select(User).where(User.id == staff_id))).scalar_one()
        assert staff.name == "New Waiter"
        assert staff.role == "waiter"

    get_resp = await client.get(f"/api/v1/staff/{staff_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "New Waiter"


@pytest.mark.asyncio
async def test_opened_shift_persists_across_fresh_sessions(fresh_session_client):
    client, session_factory = fresh_session_client
    headers, _, location_id = await _manager_headers(session_factory)

    resp = await client.post(
        f"/api/v1/locations/{location_id}/shifts/open",
        json={"openingCash": 500.0},
        headers=headers,
    )
    assert resp.status_code == 201
    shift_id = resp.json()["id"]

    async with session_factory() as verify_session:
        shift = (await verify_session.execute(select(Shift).where(Shift.id == shift_id))).scalar_one()
        assert shift.status == "open"
        assert shift.opening_cash == 500.0

    get_resp = await client.get(f"/api/v1/locations/{location_id}/shifts/current", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == shift_id

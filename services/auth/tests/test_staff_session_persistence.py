"""Regression test for get_db() commit on staff CRUD now owned by auth."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.session as session_module
from app.db.models import Business, User
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


@pytest.mark.asyncio
async def test_created_staff_persists_across_fresh_sessions(fresh_session_client):
    client, session_factory = fresh_session_client

    async with session_factory() as setup_session:
        business = Business(name="Test Restaurant", country="IL", currency="ILS")
        setup_session.add(business)
        await setup_session.flush()
        user = User(
            business_id=business.id,
            email="manager@test.com",
            name="Manager",
            role="manager",
            password_hash=hash_password("password123"),
        )
        setup_session.add(user)
        await setup_session.commit()
        token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})

    headers = {"Authorization": f"Bearer {token}"}
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

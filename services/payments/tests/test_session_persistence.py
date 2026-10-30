"""Regression test for the get_db() commit bug.

Unlike the shared-session `db`/`client` fixtures in conftest.py (which reuse one open
AsyncSession for the whole test and would mask a missing commit(), since flush()-only
changes stay visible on that same session), this test exercises the REAL, unmodified
`app.db.session.get_db` dependency (only its underlying sessionmaker is monkeypatched to
point at an isolated test engine) so each request gets its own fresh session -- mirroring
real production request handling -- and reads back through yet another independent
session after the request completes.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.session as session_module
from app.db.models import Location, Order, Payment, User
from app.db.session import Base
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def fresh_session_client(monkeypatch):
    # StaticPool: a plain in-memory sqlite DB is otherwise a separate, isolated
    # database per connection, which would falsely look like the commit didn't
    # persist just because a different pooled connection can't see it. Real
    # production Postgres has no such per-connection isolation quirk.
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # Patch the sessionmaker that the real get_db() reads by name, so we exercise the
    # actual shipped get_db() (try/commit/except-rollback) instead of a reimplementation.
    monkeypatch.setattr(session_module, "AsyncSessionLocal", session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_payment_persists_across_fresh_sessions(fresh_session_client):
    client, session_factory = fresh_session_client

    async with session_factory() as setup_session:
        user = User(
            business_id="biz-fixture",
            email="manager@test.com",
            name="Manager",
            role="manager",
            password_hash=hash_password("password123"),
        )
        setup_session.add(user)
        location = Location(business_id="biz-fixture", name="Test")
        setup_session.add(location)
        await setup_session.flush()
        order = Order(status="submitted", total=100.0, location_id=location.id)
        setup_session.add(order)
        await setup_session.commit()
        token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
        order_id = order.id

    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/payments",
        json={"orderId": order_id, "method": "cash", "amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 201
    payment_id = resp.json()["id"]

    # Same request-scoped session that created the payment is long closed by now.
    # A brand-new session must independently see the committed payment and order state.
    async with session_factory() as verify_session:
        payment = (await verify_session.execute(select(Payment).where(Payment.id == payment_id))).scalar_one()
        assert payment.status == "completed"

        refreshed_order = (await verify_session.execute(select(Order).where(Order.id == order_id))).scalar_one()
        assert refreshed_order.status == "paid"

    # And the read-back API endpoint (itself using a fresh per-request session) confirms it too.
    get_resp = await client.get(f"/api/v1/payments/{payment_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "completed"

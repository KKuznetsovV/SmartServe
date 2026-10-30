"""Shared test fixtures for the payments service test suite."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Location, Order, User
from app.db.session import Base, get_db
from app.main import app

# In-memory SQLite for tests — no Postgres needed
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DB_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession):
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession) -> tuple[User, str]:
    user = User(
        business_id="biz-fixture",
        email="manager@test.com",
        name="Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


async def create_order(db: AsyncSession, total: float, status: str = "submitted") -> Order:
    """Build an order directly against the shared DB.

    payments no longer runs alongside the ordering HTTP API in-process — see
    docs/microservices-plan.md §4 — so tests build the order fixture directly instead
    of round-tripping through the now-extracted ordering service.
    """
    location = Location(business_id="biz-fixture", name="Test")
    db.add(location)
    await db.flush()
    order = Order(status=status, total=total, location_id=location.id)
    db.add(order)
    await db.flush()
    return order

"""Shared test fixtures for the auth service test suite."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.lockout import InMemoryRedis
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Business, Location, User
from app.db.session import Base, get_db
from smartserve_shared.app_factory import limiter

from app.main import app

# In-memory SQLite for tests — no Postgres needed
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    storage = getattr(limiter, "_storage", None)
    backend = getattr(storage, "storage", None)
    if isinstance(backend, dict):
        backend.clear()


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
    app.state.redis = InMemoryRedis()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.state.redis = None
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def business(db: AsyncSession) -> Business:
    biz = Business(name="Test Restaurant", country="IL", currency="ILS")
    db.add(biz)
    await db.flush()
    return biz


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession, business: Business) -> tuple[User, str]:
    user = User(
        business_id=business.id,
        email="manager@test.com",
        name="Manager",
        role="manager",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


@pytest_asyncio.fixture
async def owner_user(db: AsyncSession, business: Business) -> tuple[User, str]:
    user = User(
        business_id=business.id,
        email="owner@test.com",
        name="Owner",
        role="owner",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.flush()
    token = create_access_token(user.id, {"business_id": user.business_id, "role": user.role})
    return user, token


@pytest_asyncio.fixture
async def location(db: AsyncSession, business: Business) -> Location:
    loc = Location(business_id=business.id, name="Main Branch")
    db.add(loc)
    await db.flush()
    return loc

"""Shared test fixtures for the SmartServe API test suite."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.db.models import Business, User
from app.core.security import hash_password, create_access_token

# In-memory SQLite for tests — no Postgres needed
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
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
async def business(db: AsyncSession) -> Business:
    biz = Business(name="Test Restaurant", country="IL", currency="ILS")
    db.add(biz)
    await db.flush()
    return biz


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

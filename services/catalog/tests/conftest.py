"""Shared test fixtures for the catalog service test suite."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.db.models import Business, Location, MenuCategory, MenuItem, User
from app.db.session import Base, get_db
from app.main import app

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


@pytest_asyncio.fixture
async def location(db: AsyncSession, business: Business) -> Location:
    loc = Location(business_id=business.id, name="Main Branch")
    db.add(loc)
    await db.flush()
    return loc


@pytest_asyncio.fixture
async def menu_item(db: AsyncSession, location: Location) -> MenuItem:
    cat = MenuCategory(location_id=location.id, name="Food", sort_order=0)
    db.add(cat)
    await db.flush()
    item = MenuItem(category_id=cat.id, name="Burger", price=50.0, tax_rate=0.17, preparation_time_min=10)
    db.add(item)
    await db.flush()
    return item

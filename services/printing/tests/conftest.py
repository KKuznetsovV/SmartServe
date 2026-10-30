"""Shared test fixtures for the printing service test suite."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Location, MenuCategory, MenuItem, User
from app.db.session import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def seed_db():
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
        session.info["allow_mirror_writes"] = True
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(seed_db: AsyncSession) -> AsyncSession:
    return seed_db


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession):
    async def _override_db():
        previous = db.info.pop("allow_mirror_writes", None)
        try:
            yield db
        finally:
            if previous:
                db.info["allow_mirror_writes"] = previous

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


@pytest_asyncio.fixture
async def location_id(db, manager_user: tuple[User, str]) -> str:
    location = Location(business_id=manager_user[0].business_id, name="Main")
    db.add(location)
    await db.flush()
    return location.id


@pytest_asyncio.fixture
async def menu_item_id(db, location_id: str) -> str:
    category = MenuCategory(location_id=location_id)
    db.add(category)
    await db.flush()
    item = MenuItem(category_id=category.id)
    db.add(item)
    await db.flush()
    return item.id

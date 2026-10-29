"""Shared test fixtures for the reporting service test suite."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from smartserve_shared.security import create_access_token, hash_password
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Location, Order, OrderItem, User
from app.db.session import Base, get_db
from app.main import app

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
async def location_id(db: AsyncSession) -> str:
    """Real Location row matching `manager_user`'s business_id ("biz-fixture") — needed
    since reports endpoints now enforce a location-ownership check against this table."""
    location = Location(id="loc-fixture", business_id="biz-fixture", name="Fixture Location")
    db.add(location)
    await db.flush()
    return location.id


async def create_paid_order(
    db: AsyncSession,
    location_id: str,
    items: list[tuple[str, int, float]],
    channel: str = "dine_in",
    status: str = "paid",
    created_by: str | None = None,
    item_meta: list[tuple[str | None, str | None, str | None]] | None = None,
) -> Order:
    """Build an order + its line items directly against the shared DB.

    items is a list of (menu_item_name, qty, unit_price) — reporting only ever reads the
    denormalized name/qty/price snapshot columns, never joins to a MenuItem row.

    item_meta, if given, is a parallel list of (menu_item_id, category_id, category_name)
    tuples for tests that need item/category grouping — defaults to all-None per item.
    """
    total = sum(qty * price for _, qty, price in items)
    order = Order(location_id=location_id, channel=channel, status=status, total=total, created_by=created_by)
    db.add(order)
    await db.flush()

    for i, (name, qty, price) in enumerate(items):
        menu_item_id, category_id, category_name = item_meta[i] if item_meta else (None, None, None)
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_name=name,
                qty=qty,
                unit_price=price,
                menu_item_id=menu_item_id,
                category_id=category_id,
                category_name=category_name,
            )
        )
    await db.flush()

    return order

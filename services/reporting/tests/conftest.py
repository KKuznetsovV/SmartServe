"""Shared test fixtures for the reporting service test suite."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.db.models import Order, OrderItem, User
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
async def location_id() -> str:
    """Order.location_id is an opaque string here (Location isn't mirrored — see db/models.py)."""
    return "loc-fixture"


async def create_paid_order(
    db: AsyncSession,
    location_id: str,
    items: list[tuple[str, int, float]],
    channel: str = "dine_in",
    status: str = "paid",
) -> Order:
    """Build an order + its line items directly against the shared DB.

    items is a list of (menu_item_name, qty, unit_price) — reporting only ever reads the
    denormalized name/qty/price snapshot columns, never joins to a MenuItem row.
    """
    total = sum(qty * price for _, qty, price in items)
    order = Order(location_id=location_id, channel=channel, status=status, total=total)
    db.add(order)
    await db.flush()

    for name, qty, price in items:
        db.add(OrderItem(order_id=order.id, menu_item_name=name, qty=qty, unit_price=price))
    await db.flush()

    return order

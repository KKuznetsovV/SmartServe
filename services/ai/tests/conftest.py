import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-32-bytes-min")

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

SECRET_KEY = os.environ["SECRET_KEY"]
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


class FakeRedis:
    """Minimal in-process Redis stand-in for unit tests."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def getdel(self, key):
        return self._store.pop(key, None)

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)

    async def aclose(self):
        pass


def make_token(*, sub="user-1", business_id="biz-1", role="manager", location_id=None):
    payload = {
        "sub": sub,
        "business_id": business_id,
        "role": role,
        "location_id": location_id,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


@pytest.fixture
def manager_token():
    return make_token(role="manager")


@pytest.fixture
def staff_token():
    return make_token(role="staff", sub="user-2")


@pytest.fixture(autouse=True)
def stub_auth_profile(request, monkeypatch):
    if request.node.get_closest_marker("real_auth_lookup"):
        return
    from smartserve_shared.security import TokenError, verify_token

    async def fake_lookup(_request, token, user_id):
        try:
            role = verify_token(token).role
        except TokenError:
            role = "manager"
        return {"id": user_id, "role": role, "active": True, "businessId": "biz-1"}

    monkeypatch.setattr("app.api.v1.deps.lookup_cached_user", fake_lookup)


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


@pytest.fixture
async def client(db: AsyncSession):
    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.state.redis = FakeRedis()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

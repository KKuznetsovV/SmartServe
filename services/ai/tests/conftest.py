import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-32-bytes-min")

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SECRET_KEY = os.environ["SECRET_KEY"]


class FakeRedis:
    """Minimal in-process Redis stand-in for unit tests."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def setex(self, key, ttl, value):
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
    payload = {"sub": sub, "business_id": business_id, "role": role, "location_id": location_id}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


@pytest.fixture
def manager_token():
    return make_token(role="manager")


@pytest.fixture
def staff_token():
    return make_token(role="staff", sub="user-2")


@pytest.fixture
async def client():
    app.state.redis = FakeRedis()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

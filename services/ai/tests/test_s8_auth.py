from types import SimpleNamespace

import pytest

from app.clients import auth_client
from app.core.config import settings

from conftest import FakeRedis


async def test_demoted_role_is_rejected(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def lookup(_request, _token, user_id):
        return {"id": user_id, "role": "waiter", "active": True, "businessId": "biz-1"}

    monkeypatch.setattr("app.api.v1.deps.lookup_cached_user", lookup)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 401


async def test_inactive_user_is_rejected(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def lookup(_request, _token, user_id):
        return {"id": user_id, "role": "manager", "active": False, "businessId": "biz-1"}

    monkeypatch.setattr("app.api.v1.deps.lookup_cached_user", lookup)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.real_auth_lookup
async def test_lookup_cached_user_hits_auth_once(monkeypatch):
    from app.api.v1.deps import lookup_cached_user

    redis = FakeRedis()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=redis)))
    calls = {"n": 0}

    class _Resp:
        def json(self):
            return {"id": "user-1", "role": "manager", "active": True, "businessId": "biz-1"}

    async def fake_get(*_args, **_kwargs):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(auth_client, "get", fake_get)
    first = await lookup_cached_user(request, "tok", "user-1")
    second = await lookup_cached_user(request, "tok", "user-1")
    assert first["role"] == "manager"
    assert second == first
    assert calls["n"] == 1

import httpx

from app.clients import auth_client
from app.core.config import settings
from app.main import app
from app.modules.ai.services import budget as budget_mod


async def _own_location(monkeypatch):
    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1", "timezone": "UTC"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)


async def test_waiter_forbidden_on_command(client, waiter_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    await _own_location(monkeypatch)
    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {waiter_token}"},
    )
    assert resp.status_code == 403


async def test_21st_command_in_a_minute_is_429(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(
        "app.modules.ai.router.local_classify",
        lambda _msg: {"intent": "unsupported.x", "confidence": 0.99, "params": {}, "preview": "no"},
    )
    await _own_location(monkeypatch)
    headers = {"Authorization": f"Bearer {manager_token}"}
    body = {"message": "hi", "context": {"locationId": "loc-1"}}
    for i in range(20):
        resp = await client.post("/api/v1/ai/command", json=body, headers=headers)
        assert resp.status_code == 200, i
    twenty_first = await client.post("/api/v1/ai/command", json=body, headers=headers)
    assert twenty_first.status_code == 429


async def test_exhausted_budget_does_not_call_anthropic(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_DAILY_CALL_BUDGET", 500)
    monkeypatch.setattr("app.modules.ai.router.local_classify", lambda _msg: None)
    await _own_location(monkeypatch)

    key = budget_mod.budget_key("biz-1", "UTC")
    await app.state.redis.set(key, "500")
    called = {"n": 0}

    async def boom(*_args, **_kwargs):
        called["n"] += 1
        raise AssertionError("Anthropic should not be called when the budget is exhausted")

    monkeypatch.setattr("app.modules.ai.services.client.create_message", boom)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 429
    assert "budget" in resp.json()["detail"].lower()
    assert called["n"] == 0


async def test_confirm_rejects_other_user(client, manager_token):
    await app.state.redis.setex(
        "ai:pending:exec-other",
        600,
        __import__("json").dumps(
            {
                "intent": "menu.create_item",
                "params": {"name": "Pizza", "price": 10},
                "context": {"locationId": "loc-1"},
                "message": "",
                "user_id": "someone-else",
                "business_id": "biz-1",
                "plan": {"intent": "menu.create_item", "scope": "items", "summary": "x", "changes": []},
            }
        ),
    )
    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-other"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404

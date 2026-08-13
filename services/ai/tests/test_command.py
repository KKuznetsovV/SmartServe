import json
from types import SimpleNamespace

from app.core.config import settings


class FakeMessage:
    def __init__(self, data, stop_reason="end_turn"):
        self.content = [SimpleNamespace(text=json.dumps(data))]
        self.stop_reason = stop_reason


async def test_command_requires_auth(client):
    resp = await client.post("/api/v1/ai/command", json={"message": "hi", "context": {}})
    assert resp.status_code in (401, 403)


async def test_command_missing_api_key(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 503


async def test_command_returns_execution_id(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_create_message(client_obj, **kwargs):
        return FakeMessage(
            {
                "intent": "menu.create_item",
                "confidence": 0.95,
                "params": {"name": "Pizza", "price": 42},
                "preview": "Create Pizza",
            }
        )

    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza for 42", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "menu.create_item"
    assert data["executionId"]
    assert data["requiresConfirmation"] is True

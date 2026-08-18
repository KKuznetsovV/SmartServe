import json
from types import SimpleNamespace

import httpx

from app.clients import auth_client, catalog_client
from app.core.config import settings
from app.main import app


class FakeMessage:
    def __init__(self, data):
        self.content = [SimpleNamespace(text=json.dumps(data))]


async def _seed_pending(execution_id, intent, params, location_id="loc-1"):
    await app.state.redis.setex(
        f"ai:pending:{execution_id}",
        600,
        json.dumps({"intent": intent, "params": params, "context": {"locationId": location_id}, "message": ""}),
    )


async def test_confirm_unknown_execution(client, manager_token):
    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "does-not-exist"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404


async def test_confirm_requires_manager(client, staff_token):
    await _seed_pending("exec-1", "menu.create_item", {"name": "Pizza", "price": 10})

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-1"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


async def test_confirm_no_token(client):
    await _seed_pending("exec-1b", "menu.create_item", {"name": "Pizza", "price": 10})

    resp = await client.post("/api/v1/ai/confirm", json={"executionId": "exec-1b"})
    assert resp.status_code in (401, 403)


async def test_confirm_location_not_owned(client, manager_token, monkeypatch):
    await _seed_pending("exec-2", "menu.create_item", {"name": "Pizza", "price": 10})

    async def fake_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "other-biz"})

    monkeypatch.setattr(auth_client, "get", fake_get)

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-2"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404


async def test_confirm_create_item_success(client, manager_token, monkeypatch):
    await _seed_pending("exec-3", "menu.create_item", {"name": "Pizza", "price": 42})

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Mains", "parentId": None}])

    async def fake_catalog_post(path, *, forward_token=None, **kwargs):
        body = kwargs["json"]
        return httpx.Response(201, json={"id": "item-1", "name": body["name"], "price": body["price"]})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "post", fake_catalog_post)

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-3"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert "Pizza" in resp.json()["message"]
    assert await app.state.redis.get("ai:pending:exec-3") is None


async def test_confirm_toggle_availability(client, manager_token, monkeypatch):
    await _seed_pending("exec-4", "menu.toggle_availability", {"name": "Pizza", "in_stock": False})

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "item-1", "name": "Pizza", "inStock": True}])

    async def fake_catalog_patch(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "item-1", "name": "Pizza", "inStock": False})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "patch", fake_catalog_patch)

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-4"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    assert "out of stock" in resp.json()["message"]


async def test_command_then_confirm_rename_item(client, manager_token, monkeypatch):
    # Exercises the full classify -> resolve -> dispatch path for a rename, not just
    # dispatch_intent() in isolation, since the bug this guards against (the identifying
    # hint and the new name colliding on the same "name" key) only shows up once a real
    # classification result flows into resolution.
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    async def fake_create_message(client_obj, **kwargs):
        return FakeMessage(
            {
                "intent": "menu.update_item",
                "confidence": 0.95,
                "params": {"item_hint": "Coke", "new_name": "Coca-Cola"},
                "preview": "Rename Coke to Coca-Cola",
            }
        )

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "item-1", "name": "Coke", "inStock": True}])

    async def fake_catalog_patch(path, *, forward_token=None, **kwargs):
        body = kwargs["json"]
        return httpx.Response(200, json={"id": "item-1", "name": body["name"]})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)
    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "patch", fake_catalog_patch)

    command_resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "Rename Coke to Coca-Cola", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert command_resp.status_code == 200
    execution_id = command_resp.json()["executionId"]

    confirm_resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": execution_id},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert confirm_resp.status_code == 200
    assert "Coca-Cola" in confirm_resp.json()["message"]

import json
from types import SimpleNamespace

import httpx

from app.clients import auth_client, catalog_client, printing_client
from app.core.config import settings
from app.main import app


class FakeMessage:
    def __init__(self, data, stop_reason="end_turn"):
        self.content = [SimpleNamespace(text=json.dumps(data))]
        self.stop_reason = stop_reason


async def test_menu_import_start(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Mains", "parentId": None}])

    async def fake_printing_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "p-1", "name": "Kitchen", "type": "kitchen"}])

    async def fake_create_message(client_obj, **kwargs):
        return FakeMessage(
            {
                "items": [{"name": "Pizza", "price": 42, "category": "Mains", "printerTypes": ["kitchen"]}],
                "message": "Found 1 item",
                "needsClarification": False,
            }
        )

    monkeypatch.setattr(auth_client, "get", fake_auth_get)
    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(printing_client, "get", fake_printing_get)
    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    resp = await client.post(
        "/api/v1/ai/menu-import",
        data={"location_id": "loc-1"},
        files={"file": ("menu.txt", b"Pizza 42", "text/plain")},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["name"] == "Pizza"
    assert data["sessionId"]


async def test_menu_import_apply(client, manager_token, monkeypatch):
    await app.state.redis.setex(
        "ai:import:sess-1",
        1800,
        json.dumps({
            "business_id": "biz-1",
            "location_id": "loc-1",
            "items": [{"name": "Pizza", "price": 42, "category": "Mains", "printerTypes": ["kitchen"]}],
            "history": [],
        }),
    )

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Mains", "parentId": None}])

    async def fake_catalog_post(path, *, forward_token=None, **kwargs):
        body = kwargs["json"]
        return httpx.Response(201, json={"id": "item-1", "name": body["name"], "price": body["price"]})

    async def fake_printing_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "p-1", "name": "Kitchen", "type": "kitchen"}])

    async def fake_printing_post(path, *, forward_token=None, **kwargs):
        return httpx.Response(201, json={"id": "route-1"})

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "post", fake_catalog_post)
    monkeypatch.setattr(printing_client, "get", fake_printing_get)
    monkeypatch.setattr(printing_client, "post", fake_printing_post)

    resp = await client.post(
        "/api/v1/ai/menu-import/apply",
        json={"sessionId": "sess-1"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["itemsCreated"] == 1
    assert data["routesCreated"] == 1
    assert await app.state.redis.get("ai:import:sess-1") is None


async def test_menu_import_apply_catalog_422_is_readable(client, manager_token, monkeypatch):
    await app.state.redis.setex(
        "ai:import:sess-q8",
        1800,
        json.dumps({
            "business_id": "biz-1",
            "location_id": "loc-1",
            "items": [{"name": "Pizza", "price": -50, "category": "Mains"}],
            "history": [],
        }),
    )

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Mains", "parentId": None}])

    async def fake_catalog_post(path, *, forward_token=None, **kwargs):
        request = httpx.Request("POST", "http://catalog/api/v1/menu/items")
        return httpx.Response(
            422,
            json={"detail": "Price must be at least 0"},
            request=request,
        )

    async def fake_printing_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[])

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "post", fake_catalog_post)
    monkeypatch.setattr(printing_client, "get", fake_printing_get)

    resp = await client.post(
        "/api/v1/ai/menu-import/apply",
        json={"sessionId": "sess-q8"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 422
    assert "0" in str(resp.json()["detail"])
    assert resp.status_code != 502


async def test_menu_import_apply_unknown_session(client, manager_token):
    resp = await client.post(
        "/api/v1/ai/menu-import/apply",
        json={"sessionId": "does-not-exist"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404

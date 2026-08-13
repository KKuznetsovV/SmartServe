import httpx

from app.clients import auth_client, catalog_client
from app.modules.ai import router as router_module


def _seed_pending(execution_id, intent, params, location_id="loc-1"):
    router_module._pending[execution_id] = {
        "intent": intent,
        "params": params,
        "context": {"locationId": location_id},
    }


async def test_confirm_unknown_execution(client, manager_token):
    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "does-not-exist"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404


async def test_confirm_requires_manager(client, staff_token):
    _seed_pending("exec-1", "menu.create_item", {"name": "Pizza", "price": 10})

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-1"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


async def test_confirm_no_token(client):
    _seed_pending("exec-1b", "menu.create_item", {"name": "Pizza", "price": 10})

    resp = await client.post("/api/v1/ai/confirm", json={"executionId": "exec-1b"})
    assert resp.status_code in (401, 403)


async def test_confirm_location_not_owned(client, manager_token, monkeypatch):
    _seed_pending("exec-2", "menu.create_item", {"name": "Pizza", "price": 10})

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
    _seed_pending("exec-3", "menu.create_item", {"name": "Pizza", "price": 42})

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
    assert "exec-3" not in router_module._pending


async def test_confirm_toggle_availability(client, manager_token, monkeypatch):
    _seed_pending("exec-4", "menu.toggle_availability", {"name": "Pizza", "in_stock": False})

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

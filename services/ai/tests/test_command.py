import json
from types import SimpleNamespace

import httpx

from app.clients import auth_client, catalog_client, reporting_client
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

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 503


async def test_command_missing_location_context(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 400


async def test_command_location_not_owned(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-999", "businessId": "some-other-biz"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "add a pizza", "context": {"locationId": "loc-999"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 404


async def test_command_returns_execution_id(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    async def fake_create_message(*_args, **kwargs):
        return FakeMessage(
            {
                "intent": "menu.create_item",
                "confidence": 0.95,
                "params": {"name": "Pizza", "price": 42},
                "preview": "Create Pizza",
            }
        )

    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=[{"id": "cat-1", "name": "Mains", "parentId": None}])

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)

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


async def test_command_report_query_bypasses_confirm(client, manager_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    async def fake_create_message(*_args, **kwargs):
        return FakeMessage(
            {
                "intent": "report.query",
                "confidence": 0.95,
                "params": {"report_type": "sales", "group_by": "item", "start": "2026-01-01", "end": "2026-01-31"},
                "preview": "Sales by item for January",
            }
        )

    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    async def fake_reporting_get(path, *, forward_token=None, **kwargs):
        assert path == "/api/v1/locations/loc-1/reports/sales"
        assert kwargs["params"]["group_by"] == "item"
        return httpx.Response(
            200,
            json={
                "groupBy": "item",
                "start": "2026-01-01T00:00:00+00:00",
                "end": "2026-01-31T23:59:59.999999+00:00",
                "rows": [{"groupId": "item-1", "groupLabel": "Burger", "qty": 5, "revenue": 250.0}],
                "totalQty": 5,
                "totalRevenue": 250.0,
            },
        )

    monkeypatch.setattr(reporting_client, "get", fake_reporting_get)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "how many burgers did we sell in January", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "report.query"
    assert data["requiresConfirmation"] is False
    assert "executionId" not in data
    assert data["report"]["rows"][0]["groupLabel"] == "Burger"


async def test_command_report_query_requires_manager_role(client, staff_token, monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    monkeypatch.setattr(auth_client, "get", fake_auth_get)

    async def fake_create_message(*_args, **kwargs):
        return FakeMessage(
            {
                "intent": "report.query",
                "confidence": 0.95,
                "params": {"report_type": "sales", "start": "2026-01-01", "end": "2026-01-31"},
                "preview": "Sales report",
            }
        )

    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": "how many burgers did we sell", "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403

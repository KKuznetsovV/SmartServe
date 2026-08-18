"""Test for the ai.action_executed publish call site (mocked mq.publish, no live broker)."""

from unittest.mock import AsyncMock, patch

import httpx

from app.clients import auth_client, catalog_client
from app.main import app


async def _seed_pending(execution_id, intent, params, location_id="loc-1"):
    import json

    await app.state.redis.setex(
        f"ai:pending:{execution_id}",
        600,
        json.dumps({"intent": intent, "params": params, "context": {"locationId": location_id}, "message": ""}),
    )


async def test_confirm_publishes_ai_action_executed(client, manager_token, monkeypatch):
    await _seed_pending("exec-events-1", "menu.create_item", {"name": "Pizza", "price": 42})

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

    with patch("app.core.mq.publish", new_callable=AsyncMock) as mock_publish:
        resp = await client.post(
            "/api/v1/ai/confirm",
            json={"executionId": "exec-events-1"},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
    assert resp.status_code == 200

    mock_publish.assert_awaited_once()
    _, routing_key, payload = mock_publish.await_args.args
    assert routing_key == "ai.action_executed"
    assert payload["intent"] == "menu.create_item"
    assert payload["locationId"] == "loc-1"
    assert payload["businessId"] == "biz-1"
    assert payload["userId"]
    assert "originalMessage" in payload

"""Test for the ai.action_executed outbox row (no live broker)."""

import json

import httpx
from sqlalchemy import select

from app.clients import auth_client, catalog_client
from app.db.models import Outbox
from app.main import app


async def _seed_pending(execution_id, intent, params, location_id="loc-1"):
    await app.state.redis.setex(
        f"ai:pending:{execution_id}",
        600,
        json.dumps(
            {
                "intent": intent,
                "params": params,
                "context": {"locationId": location_id},
                "message": "",
                "user_id": "user-1",
                "business_id": "biz-1",
                "plan": {
                    "intent": intent,
                    "scope": "items",
                    "summary": f"Created '{params['name']}' ({params['price']:.2f}) in 'Mains'",
                    "changes": [
                        {
                            "entity": "item",
                            "id": None,
                            "name": params["name"],
                            "field": "create",
                            "from": None,
                            "to": {"name": params["name"], "price": float(params["price"]), "categoryId": "cat-1"},
                            "extra": {"categoryId": "cat-1"},
                        }
                    ],
                },
            }
        ),
    )


async def test_confirm_enqueues_ai_action_executed(client, manager_token, db, monkeypatch):
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

    resp = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": "exec-events-1"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert resp.status_code == 200

    db.expire_all()
    row = (await db.execute(select(Outbox))).scalar_one()
    assert row.routing_key == "ai.action_executed"
    payload = json.loads(row.payload)
    assert payload["intent"] == "menu.create_item"
    assert payload["locationId"] == "loc-1"
    assert payload["businessId"] == "biz-1"
    assert payload["userId"]
    assert payload["eventId"]
    assert "originalMessage" in payload
    assert "occurredAt" in payload

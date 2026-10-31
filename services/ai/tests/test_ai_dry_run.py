import json
from types import SimpleNamespace

import httpx

from app.clients import auth_client, catalog_client
from app.core.config import settings
from app.main import app

CATEGORIES = [
    {"id": "cat-drinks", "name": "Drinks", "nameHe": "משקאות", "parentId": None},
    {"id": "cat-mains", "name": "Mains", "nameHe": "עיקריות", "parentId": None},
]
ITEMS = [
    {"id": "item-cola", "name": "Cola", "nameHe": "קולה", "price": 12.0, "inStock": True, "categoryId": "cat-drinks"},
    {
        "id": "item-lemonade",
        "name": "Lemonade",
        "nameHe": "לימונדה",
        "price": 14.0,
        "inStock": True,
        "categoryId": "cat-drinks",
    },
    {
        "id": "item-burger",
        "name": "Burger",
        "nameHe": "המבורגר",
        "price": 68.0,
        "inStock": True,
        "categoryId": "cat-mains",
    },
    {
        "id": "item-salmon",
        "name": "Salmon Fillet",
        "nameHe": "פילה סלמון",
        "price": 94.0,
        "inStock": True,
        "categoryId": "cat-mains",
    },
]


def _demo_catalog(path: str, items_by_id: dict):
    if path.endswith("/categories"):
        return CATEGORIES
    if path.endswith("/stock"):
        return list(items_by_id.values())
    if "/items/" in path:
        return items_by_id[path.rsplit("/", 1)[-1]]
    return []


class FakeMessage:
    def __init__(self, data, stop_reason="end_turn"):
        self.content = [SimpleNamespace(text=json.dumps(data))]
        self.stop_reason = stop_reason


def _auth_ok():
    async def fake_auth_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json={"id": "loc-1", "businessId": "biz-1"})

    return fake_auth_get


def _catalog():
    items_by_id = {item["id"]: dict(item) for item in ITEMS}

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=_demo_catalog(path, items_by_id))

    return fake_catalog_get, items_by_id


async def _command(client, token, monkeypatch, payload, message):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(auth_client, "get", _auth_ok())
    fake_get, store = _catalog()
    monkeypatch.setattr(catalog_client, "get", fake_get)

    async def fake_create_message(*_args, **kwargs):
        return FakeMessage(payload)

    monkeypatch.setattr("app.modules.ai.router.create_message", fake_create_message)

    resp = await client.post(
        "/api/v1/ai/command",
        json={"message": message, "context": {"locationId": "loc-1"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp, store


async def test_hebrew_raise_drinks_only_touches_drinks(client, manager_token, monkeypatch):
    resp, _ = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "menu.bulk_price_change",
            "confidence": 0.95,
            "params": {"category_hint": "משקאות", "change_pct": 10},
            "preview": "העלאת מחירי משקאות ב-10%",
        },
        "תעלה את כל המשקאות ב-10%",
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = {row["id"] for row in data["changes"]}
    assert ids == {"item-cola", "item-lemonade"}
    assert data["scope"] == "category"
    assert data["executionId"]
    cola = next(row for row in data["changes"] if row["id"] == "item-cola")
    assert cola["from"] == 12.0
    assert cola["to"] == 13.2
    lemonade = next(row for row in data["changes"] if row["id"] == "item-lemonade")
    assert lemonade["from"] == 14.0
    assert lemonade["to"] == 15.4


async def test_hebrew_burger_price_resolves_name_he(client, manager_token, monkeypatch):
    resp, _ = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "menu.update_item",
            "confidence": 0.95,
            "params": {"item_hint": "המבורגר", "price": 72},
            "preview": "עדכון מחיר המבורגר",
        },
        "תעלה את המחיר של ההמבורגר ל-72",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["changes"] == [
        {
            "entity": "item",
            "id": "item-burger",
            "name": "Burger",
            "field": "price",
            "from": 68.0,
            "to": 72.0,
        }
    ]


async def test_salmon_86_toggles_stock_not_price(client, manager_token, monkeypatch):
    resp, _ = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "menu.toggle_availability",
            "confidence": 0.97,
            "params": {"item_hint": "salmon", "in_stock": False},
            "preview": "Mark salmon out of stock",
        },
        "the salmon is 86 for tonight",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "menu.toggle_availability"
    assert data["changes"] == [
        {
            "entity": "item",
            "id": "item-salmon",
            "name": "Salmon Fillet",
            "field": "inStock",
            "from": True,
            "to": False,
        }
    ]
    assert all(row["field"] != "price" for row in data["changes"])


async def test_add_waiter_is_unsupported(client, manager_token, monkeypatch):
    resp, _ = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "staff.add_user",
            "confidence": 0.96,
            "params": {"name": "Dana", "role": "waiter"},
            "preview": "Add Dana as a waiter",
        },
        "add Dana as a new waiter",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["supported"] is False
    assert data.get("executionId") is None
    assert data["requiresConfirmation"] is False
    assert data["message"]


async def test_confirm_409_when_menu_changed(client, manager_token, monkeypatch):
    resp, store = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "menu.update_item",
            "confidence": 0.95,
            "params": {"item_hint": "Burger", "price": 72},
            "preview": "Set burger to 72",
        },
        "set the burger to 72",
    )
    assert resp.status_code == 200
    execution_id = resp.json()["executionId"]
    store["item-burger"]["price"] = 80.0

    confirm = await client.post(
        "/api/v1/ai/confirm",
        json={"executionId": execution_id},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert confirm.status_code == 409
    assert "the menu changed since the preview" in str(confirm.json()["detail"])
    assert await app.state.redis.get(f"ai:pending:{execution_id}") is None


async def test_unmatched_hint_returns_suggestions(client, manager_token, monkeypatch):
    resp, _ = await _command(
        client,
        manager_token,
        monkeypatch,
        {
            "intent": "menu.update_item",
            "confidence": 0.9,
            "params": {"item_hint": "sushi", "price": 50},
            "preview": "Update sushi",
        },
        "make the sushi 50",
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "suggestions" in detail
    assert len(detail["suggestions"]) <= 3

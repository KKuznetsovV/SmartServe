import httpx
import pytest

from app.clients import catalog_client, printing_client
from app.modules.ai.services.dispatch import dispatch_intent, fuzzy_match
from app.modules.ai.services.menu_client import MenuClient, PrintingClient


def test_fuzzy_match_exact():
    assert fuzzy_match("Pizza", ["Burger", "Pizza", "Salad"]) == 1


def test_fuzzy_match_partial():
    assert fuzzy_match("piz", ["Burger", "Margherita Pizza", "Salad"]) == 1


def test_fuzzy_match_none_hint():
    assert fuzzy_match(None, ["Burger"]) is None


def test_fuzzy_match_no_match():
    assert fuzzy_match("Sushi", ["Burger", "Pizza"]) is None


ITEMS = [
    {"id": "item-bar-1", "name": "Beer", "categoryId": "cat-bar"},
    {"id": "item-bar-2", "name": "Wine", "categoryId": "cat-bar"},
    {"id": "item-food-1", "name": "Burger", "categoryId": "cat-food"},
]
CATEGORIES = [
    {"id": "cat-bar", "name": "Bar"},
    {"id": "cat-food", "name": "Food"},
]
PRINTERS = [
    {"id": "printer-kitchen", "name": "Main Kitchen", "type": "kitchen"},
    {"id": "printer-receipt", "name": "Front Receipt", "type": "receipt"},
]


@pytest.mark.asyncio
async def test_dispatch_printer_route_by_category_replaces_existing(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        if path.endswith("/categories"):
            return httpx.Response(200, json=CATEGORIES)
        return httpx.Response(200, json=ITEMS)

    async def fake_printing_get(path, *, forward_token=None, **kwargs):
        if path.endswith("/printers"):
            return httpx.Response(200, json=PRINTERS)
        return httpx.Response(
            200,
            json=[{"id": "route-1", "itemId": "item-bar-1", "printerId": "printer-receipt"}],
        )

    deleted_routes: list[str] = []
    added_routes: list[tuple[str, str]] = []

    async def fake_printing_delete(path, *, forward_token=None, **kwargs):
        deleted_routes.append(path.rsplit("/", 1)[-1])
        return httpx.Response(204)

    async def fake_printing_post(path, *, forward_token=None, **kwargs):
        body = kwargs["json"]
        added_routes.append((body["printer_id"], body["item_id"]))
        return httpx.Response(201, json={"id": "route-new", **body})

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(printing_client, "get", fake_printing_get)
    monkeypatch.setattr(printing_client, "delete", fake_printing_delete)
    monkeypatch.setattr(printing_client, "post", fake_printing_post)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    result = await dispatch_intent(
        "printer.route",
        {"category_hint": "Bar", "printer_hint": "kitchen"},
        "loc-1",
        menu,
        printing,
    )

    assert "Beer" in result and "Wine" in result and "Main Kitchen" in result
    assert deleted_routes == ["route-1"]
    assert ("printer-kitchen", "item-bar-1") in added_routes
    assert ("printer-kitchen", "item-bar-2") in added_routes


@pytest.mark.asyncio
async def test_dispatch_printer_route_no_matching_printer(monkeypatch):
    async def fake_printing_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=PRINTERS)

    monkeypatch.setattr(printing_client, "get", fake_printing_get)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    with pytest.raises(Exception) as exc_info:
        await dispatch_intent(
            "printer.route",
            {"category_hint": "Bar", "printer_hint": "label"},
            "loc-1",
            menu,
            printing,
        )
    assert "404" in str(exc_info.value) or "No printer" in str(exc_info.value)


TRASHED_ITEMS = [
    {"id": "item-trashed-1", "name": "Discontinued Soup", "categoryId": "cat-food"},
]


@pytest.mark.asyncio
async def test_dispatch_move_to_trash(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=ITEMS)

    deleted_paths: list[str] = []

    async def fake_catalog_delete(path, *, forward_token=None, **kwargs):
        deleted_paths.append(path)
        return httpx.Response(204)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "delete", fake_catalog_delete)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    result = await dispatch_intent("menu.move_to_trash", {"item_hint": "Burger"}, "loc-1", menu, printing)

    assert "Burger" in result
    assert deleted_paths == ["/api/v1/menu/items/item-food-1"]


@pytest.mark.asyncio
async def test_dispatch_move_to_trash_no_match(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=ITEMS)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    with pytest.raises(Exception) as exc_info:
        await dispatch_intent("menu.move_to_trash", {"item_hint": "Sushi"}, "loc-1", menu, printing)
    assert "404" in str(exc_info.value) or "No item" in str(exc_info.value)


CATEGORIES_NESTED = [
    {"id": "cat-drinks", "name": "Drinks", "parentId": None},
    {"id": "cat-soft-drinks", "name": "Soft Drinks", "parentId": "cat-drinks"},
    {"id": "cat-food", "name": "Food", "parentId": None},
]
ITEMS_NESTED = [
    {"id": "item-beer", "name": "Beer", "categoryId": "cat-drinks"},
    {"id": "item-cola", "name": "Cola", "categoryId": "cat-soft-drinks"},
    {"id": "item-burger", "name": "Burger", "categoryId": "cat-food"},
]


@pytest.mark.asyncio
async def test_dispatch_move_to_trash_by_category_trashes_descendants(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        if path.endswith("/categories"):
            return httpx.Response(200, json=CATEGORIES_NESTED)
        return httpx.Response(200, json=ITEMS_NESTED)

    deleted_paths: list[str] = []

    async def fake_catalog_delete(path, *, forward_token=None, **kwargs):
        deleted_paths.append(path)
        return httpx.Response(204)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "delete", fake_catalog_delete)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    result = await dispatch_intent("menu.move_to_trash", {"category_hint": "Drinks"}, "loc-1", menu, printing)

    # "Drinks" (direct: Beer) plus its child "Soft Drinks" (Cola) — not "Food" (Burger).
    assert sorted(deleted_paths) == sorted(["/api/v1/menu/items/item-beer", "/api/v1/menu/items/item-cola"])
    assert "2" in result and "Drinks" in result


@pytest.mark.asyncio
async def test_dispatch_move_to_trash_by_category_no_items(monkeypatch):
    empty_category_items = [i for i in ITEMS_NESTED if i["categoryId"] != "cat-food"]

    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        if path.endswith("/categories"):
            return httpx.Response(200, json=CATEGORIES_NESTED)
        return httpx.Response(200, json=empty_category_items)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    with pytest.raises(Exception) as exc_info:
        await dispatch_intent("menu.move_to_trash", {"category_hint": "Food"}, "loc-1", menu, printing)
    assert "404" in str(exc_info.value) or "No items found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_restore_item(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        assert path.endswith("/trash")
        return httpx.Response(200, json=TRASHED_ITEMS)

    async def fake_catalog_post(path, *, forward_token=None, **kwargs):
        assert path == "/api/v1/menu/items/item-trashed-1/restore"
        return httpx.Response(200, json={**TRASHED_ITEMS[0], "deletedAt": None})

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "post", fake_catalog_post)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    result = await dispatch_intent("menu.restore_item", {"item_hint": "Discontinued Soup"}, "loc-1", menu, printing)
    assert "Discontinued Soup" in result


@pytest.mark.asyncio
async def test_dispatch_restore_item_not_in_trash(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        return httpx.Response(200, json=TRASHED_ITEMS)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    with pytest.raises(Exception) as exc_info:
        await dispatch_intent("menu.restore_item", {"item_hint": "Burger"}, "loc-1", menu, printing)
    assert "404" in str(exc_info.value) or "No trashed item" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dispatch_permanently_delete_item(monkeypatch):
    async def fake_catalog_get(path, *, forward_token=None, **kwargs):
        assert path.endswith("/trash")
        return httpx.Response(200, json=TRASHED_ITEMS)

    deleted_paths: list[str] = []

    async def fake_catalog_delete(path, *, forward_token=None, **kwargs):
        deleted_paths.append(path)
        return httpx.Response(204)

    monkeypatch.setattr(catalog_client, "get", fake_catalog_get)
    monkeypatch.setattr(catalog_client, "delete", fake_catalog_delete)

    menu = MenuClient("tok")
    printing = PrintingClient("tok")

    result = await dispatch_intent(
        "menu.permanently_delete_item", {"item_hint": "Discontinued Soup"}, "loc-1", menu, printing
    )

    assert "Discontinued Soup" in result
    assert deleted_paths == ["/api/v1/menu/items/item-trashed-1/permanent"]

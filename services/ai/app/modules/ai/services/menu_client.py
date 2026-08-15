"""HTTP-backed replacement for the old in-process MenuService/Printer queries — ai owns
no DB (see docs/microservices-plan.md §4), so every read/write goes through
services/catalog's and services/printing's REST APIs instead. Every method mirrors the
shape of the equivalent MenuService/PrinterService method; results are plain dicts with
camelCase keys since that's how those services serialize responses (response_model_by_alias).
"""

from typing import Any

from app.clients import catalog_client, printing_client


class MenuClient:
    def __init__(self, token: str):
        self._token = token

    async def list_categories(self, location_id: str) -> list[dict[str, Any]]:
        resp = await catalog_client.get(f"/api/v1/menu/locations/{location_id}/categories", forward_token=self._token)
        return resp.json()

    async def create_category(
        self, *, location_id: str, name: str, parent_id: str | None = None, sort_order: int = 0
    ) -> dict[str, Any]:
        body = {"location_id": location_id, "name": name, "parent_id": parent_id, "sort_order": sort_order}
        resp = await catalog_client.post("/api/v1/menu/categories", json=body, forward_token=self._token)
        return resp.json()

    async def update_category(self, category_id: str, **fields: Any) -> dict[str, Any]:
        resp = await catalog_client.patch(
            f"/api/v1/menu/categories/{category_id}", json=fields, forward_token=self._token
        )
        return resp.json()

    async def list_all_items(self, location_id: str) -> list[dict[str, Any]]:
        resp = await catalog_client.get(f"/api/v1/menu/locations/{location_id}/stock", forward_token=self._token)
        return resp.json()

    async def create_item(
        self,
        *,
        category_id: str,
        name: str,
        price: float,
        name_he: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        body = {
            "category_id": category_id,
            "name": name,
            "name_he": name_he,
            "description": description,
            "price": price,
        }
        resp = await catalog_client.post("/api/v1/menu/items", json=body, forward_token=self._token)
        return resp.json()

    async def update_item(self, item_id: str, **fields: Any) -> dict[str, Any]:
        resp = await catalog_client.patch(f"/api/v1/menu/items/{item_id}", json=fields, forward_token=self._token)
        return resp.json()

    async def bulk_price_update(
        self,
        *,
        location_id: str,
        category_id: str | None,
        change_pct: float | None,
        change_abs: float | None,
    ) -> int:
        body = {
            "location_id": location_id,
            "category_id": category_id,
            "change_pct": change_pct,
            "change_abs": change_abs,
        }
        resp = await catalog_client.post("/api/v1/menu/items/bulk-price", json=body, forward_token=self._token)
        return resp.json()["updated"]

    async def set_stock(self, item_id: str, in_stock: bool) -> dict[str, Any]:
        resp = await catalog_client.patch(
            f"/api/v1/menu/items/{item_id}/stock", json={"in_stock": in_stock}, forward_token=self._token
        )
        return resp.json()

    async def list_trashed_items(self, location_id: str) -> list[dict[str, Any]]:
        resp = await catalog_client.get(f"/api/v1/menu/locations/{location_id}/trash", forward_token=self._token)
        return resp.json()

    async def move_to_trash(self, item_id: str) -> None:
        await catalog_client.delete(f"/api/v1/menu/items/{item_id}", forward_token=self._token)

    async def restore_item(self, item_id: str) -> dict[str, Any]:
        resp = await catalog_client.post(f"/api/v1/menu/items/{item_id}/restore", forward_token=self._token)
        return resp.json()

    async def permanently_delete_item(self, item_id: str) -> None:
        await catalog_client.delete(f"/api/v1/menu/items/{item_id}/permanent", forward_token=self._token)


class PrintingClient:
    def __init__(self, token: str):
        self._token = token

    async def list_printers(self, location_id: str) -> list[dict[str, Any]]:
        resp = await printing_client.get(f"/api/v1/locations/{location_id}/printers", forward_token=self._token)
        return resp.json()

    async def add_route(self, printer_id: str, item_id: str) -> dict[str, Any]:
        """Idempotent on (printer_id, item_id) — safe to call even if the route already exists."""
        resp = await printing_client.post(
            "/api/v1/printer-routes", json={"printer_id": printer_id, "item_id": item_id}, forward_token=self._token
        )
        return resp.json()

    async def list_routes(self, location_id: str) -> list[dict[str, Any]]:
        resp = await printing_client.get(f"/api/v1/locations/{location_id}/printer-routes", forward_token=self._token)
        return resp.json()

    async def delete_route(self, route_id: str) -> None:
        await printing_client.delete(f"/api/v1/printer-routes/{route_id}", forward_token=self._token)

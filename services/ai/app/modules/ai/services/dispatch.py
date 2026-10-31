"""Dry-run plans and confirmed execution of AI catalog/printing commands."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException, status
from smartserve_shared.money import money

from app.core.config import settings
from app.modules.ai.services.client import create_message, parse_json_reply
from app.modules.ai.services.match import MatchError, match_index
from app.modules.ai.services.menu_client import MenuClient, PrintingClient
from app.modules.ai.services.prompts import MENU_REORG_SYSTEM_PROMPT

Scope = Literal["items", "category", "location"]

IMPLEMENTED_INTENTS = frozenset(
    {
        "menu.create_item",
        "menu.update_item",
        "menu.bulk_price_change",
        "menu.toggle_availability",
        "menu.create_category",
        "menu.reorganize_categories",
        "menu.move_items_to_category",
        "menu.move_to_trash",
        "menu.restore_item",
        "menu.permanently_delete_item",
        "printer.route",
    }
)

STALE_PREVIEW = "the menu changed since the preview"


@dataclass
class Change:
    entity: str
    id: str | None
    name: str
    field: str
    from_value: Any
    to_value: Any
    extra: dict[str, Any] = dc_field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        body = {
            "entity": self.entity,
            "id": self.id,
            "name": self.name,
            "field": self.field,
            "from": self.from_value,
            "to": self.to_value,
        }
        if self.extra:
            body["extra"] = self.extra
        return body

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Change:
        return cls(
            entity=raw["entity"],
            id=raw.get("id"),
            name=raw["name"],
            field=raw["field"],
            from_value=raw.get("from"),
            to_value=raw.get("to"),
            extra=raw.get("extra") or {},
        )


@dataclass
class Plan:
    changes: list[Change]
    scope: Scope
    summary: str
    intent: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "changes": [change.as_dict() for change in self.changes],
            "scope": self.scope,
            "summary": self.summary,
            "intent": self.intent,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Plan:
        return cls(
            changes=[Change.from_dict(row) for row in raw.get("changes") or []],
            scope=raw.get("scope") or "items",
            summary=raw.get("summary") or "",
            intent=raw.get("intent") or "",
        )


def fuzzy_match(hint: str | None, names: list[str]) -> int | None:
    """Return the index of the best case-insensitive match, or None if nothing matches."""
    if not hint:
        return None
    records = [{"name": name} for name in names]
    try:
        return match_index(hint, records, keys=("name",))
    except MatchError:
        return None


def _http_match(exc: MatchError, kind: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"message": f"No {kind} matching '{exc.hint}' was found", "suggestions": exc.suggestions},
    )


def _require_match(hint: str | None, records: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    try:
        idx = match_index(hint, records)
    except MatchError as exc:
        raise _http_match(exc, kind) from exc
    if idx is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not determine which {kind}")
    return records[idx]


def _explicit_location_scope(params: dict[str, Any], classifier_scope: str | None) -> bool:
    raw = classifier_scope or params.get("scope")
    return str(raw or "").strip().lower() == "location"


def _hebrew(message: str) -> bool:
    return any("\u0590" <= ch <= "\u05ff" for ch in message)


def _summarize(changes: list[Change], scope: Scope, *, hebrew: bool) -> str:
    count = len(changes)
    if hebrew:
        if scope == "location":
            return f"{count} שינויים בכל התפריט"
        if scope == "category":
            return f"{count} שינויים בקטגוריה"
        return f"{count} שינויים"
    if scope == "location":
        return f"{count} change(s) across the whole menu"
    if scope == "category":
        return f"{count} change(s) in this category"
    return f"{count} change(s)"


def _item_price(item: dict[str, Any]) -> Decimal:
    return money(item.get("price") or 0)


async def plan_intent(
    intent: str,
    params: dict[str, Any],
    location_id: str,
    menu: MenuClient,
    printing: PrintingClient,
    *,
    classifier_scope: str | None = None,
    original_message: str = "",
) -> Plan:
    if intent not in IMPLEMENTED_INTENTS:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"'{intent}' isn't automated yet — please make this change manually",
        )
    if intent == "printer.route":
        plan = await _plan_printer_route(params, location_id, menu, printing)
    elif intent == "menu.create_category":
        plan = await _plan_create_category(params, location_id, menu)
    elif intent == "menu.reorganize_categories":
        plan = await _plan_reorganize_categories(params, location_id, menu)
    elif intent == "menu.move_items_to_category":
        plan = await _plan_move_items(params, location_id, menu)
    elif intent == "menu.create_item":
        plan = await _plan_create_item(params, location_id, menu)
    elif intent == "menu.update_item":
        plan = await _plan_update_item(params, location_id, menu)
    elif intent == "menu.bulk_price_change":
        plan = await _plan_bulk_price(params, location_id, menu, classifier_scope=classifier_scope)
    elif intent == "menu.toggle_availability":
        plan = await _plan_toggle_availability(params, location_id, menu)
    elif intent == "menu.move_to_trash":
        plan = await _plan_trash(params, location_id, menu)
    elif intent == "menu.restore_item":
        plan = await _plan_restore(params, location_id, menu)
    elif intent == "menu.permanently_delete_item":
        plan = await _plan_permanent_delete(params, location_id, menu)
    else:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=f"'{intent}' isn't automated yet")
    plan.intent = intent
    if not plan.summary:
        plan.summary = _summarize(plan.changes, plan.scope, hebrew=_hebrew(original_message))
    return plan


async def dispatch_intent(
    intent: str, params: dict, location_id: str, menu: MenuClient, printing: PrintingClient
) -> str:
    """Execute a command by planning then applying — used by older tests and as a fallback."""
    plan = await plan_intent(intent, params, location_id, menu, printing)
    return await apply_plan(plan, location_id, menu, printing)


async def assert_plan_fresh(plan: Plan, menu: MenuClient) -> None:
    for change in plan.changes:
        if change.field == "create" or change.id in (None, ""):
            continue
        current = await _current_value(change, menu)
        if not _same_value(change.field, current, change.from_value):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=STALE_PREVIEW)


def _same_value(field_name: str, current: Any, expected: Any) -> bool:
    if field_name == "price":
        try:
            return money(current) == money(expected)
        except Exception:
            return False
    return current == expected


async def _current_value(change: Change, menu: MenuClient) -> Any:
    if change.entity == "item":
        if change.field in ("deleted", "restored", "permanentlyDeleted"):
            if change.field == "deleted":
                item = await menu.get_item(change.id or "")
                return bool(item.get("deletedAt"))
            return change.from_value
        item = await menu.get_item(change.id or "")
        if change.field == "inStock":
            return item.get("inStock")
        if change.field == "price":
            return item.get("price")
        if change.field == "name":
            return item.get("name")
        if change.field == "description":
            return item.get("description")
        if change.field == "categoryId":
            return item.get("categoryId")
        if change.field == "printerRoute":
            return change.from_value
        return item.get(change.field)
    if change.entity == "category" and change.field == "parentId":
        return change.from_value
    return change.from_value


async def apply_plan(plan: Plan, location_id: str, menu: MenuClient, printing: PrintingClient) -> str:
    applied: list[str] = []
    try:
        for change in plan.changes:
            await _apply_change(change, location_id, menu, printing)
            applied.append(change.name)
    except HTTPException as exc:
        if applied:
            detail = exc.detail
            message = detail if isinstance(detail, str) else str(detail)
            raise HTTPException(
                status_code=exc.status_code,
                detail={"message": message, "applied": applied},
            ) from exc
        raise
    if plan.summary:
        return plan.summary
    return f"Updated {len(applied)} item(s)"


async def _apply_change(change: Change, location_id: str, menu: MenuClient, printing: PrintingClient) -> None:
    if change.field == "create" and change.entity == "category":
        await menu.create_category(
            location_id=location_id,
            name=str(change.to_value),
            parent_id=change.extra.get("parentId"),
        )
        return
    if change.field == "create" and change.entity == "item":
        payload = change.to_value if isinstance(change.to_value, dict) else {}
        category_id = payload.get("categoryId") or change.extra.get("categoryId")
        if not category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing category for new item")
        await menu.create_item(
            category_id=str(category_id),
            name=str(payload.get("name") or change.name),
            price=payload.get("price") or 0,
            name_he=payload.get("nameHe"),
            description=payload.get("description"),
        )
        return
    if change.entity == "item" and change.id:
        if change.field == "price":
            await menu.update_item(change.id, price=float(money(change.to_value)))
            return
        if change.field == "name":
            await menu.update_item(change.id, name=change.to_value)
            return
        if change.field == "description":
            await menu.update_item(change.id, description=change.to_value)
            return
        if change.field == "categoryId":
            await menu.update_item(change.id, category_id=change.to_value)
            return
        if change.field == "inStock":
            await menu.set_stock(change.id, bool(change.to_value))
            return
        if change.field == "deleted":
            await menu.move_to_trash(change.id)
            return
        if change.field == "restored":
            await menu.restore_item(change.id)
            return
        if change.field == "permanentlyDeleted":
            await menu.permanently_delete_item(change.id)
            return
        if change.field == "printerRoute":
            for route_id in change.extra.get("deleteRouteIds") or []:
                await printing.delete_route(route_id)
            await printing.add_route(str(change.to_value), change.id)
            return
    if change.entity == "category" and change.id and change.field == "parentId":
        await menu.update_category(change.id, parent_id=change.to_value)
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot apply {change.field} on {change.entity}"
    )


async def _plan_create_category(params: dict, location_id: str, menu: MenuClient) -> Plan:
    name = params.get("name") or params.get("category_name")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the category name")
    parent_id = None
    parent_hint = params.get("parent_name") or params.get("parent") or params.get("parent_category")
    if parent_hint:
        categories = await menu.list_categories(location_id)
        parent = _require_match(parent_hint, categories, "category")
        parent_id = parent["id"]
    change = Change(
        entity="category",
        id=None,
        name=str(name),
        field="create",
        from_value=None,
        to_value=str(name),
        extra={"parentId": parent_id},
    )
    return Plan(
        changes=[change],
        scope="items",
        summary=f"Created category '{name}'" + (" as a subcategory" if parent_id else ""),
    )


async def _plan_create_item(params: dict, location_id: str, menu: MenuClient) -> Plan:
    name = params.get("name")
    price = params.get("price")
    if not name or price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the item name and price"
        )
    categories = await menu.list_categories(location_id)
    if not categories:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No categories exist yet for this item")
    category_hint = params.get("category_hint") or params.get("category")
    if category_hint:
        category = _require_match(category_hint, categories, "category")
    else:
        category = categories[0]
    change = Change(
        entity="item",
        id=None,
        name=str(name),
        field="create",
        from_value=None,
        to_value={"name": name, "price": float(money(price)), "categoryId": category["id"]},
        extra={"categoryId": category["id"]},
    )
    return Plan(
        changes=[change],
        scope="items",
        summary=f"Created '{name}' ({money(price):.2f}) in '{category['name']}'",
    )


async def _plan_update_item(params: dict, location_id: str, menu: MenuClient) -> Plan:
    item = await _resolve_item(params, location_id, menu)
    changes: list[Change] = []
    if "price" in params or "new_price" in params:
        new_price = money(params.get("price", params.get("new_price")))
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="price",
                from_value=float(_item_price(item)),
                to_value=float(new_price),
            )
        )
    if "description" in params:
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="description",
                from_value=item.get("description"),
                to_value=params["description"],
            )
        )
    new_name = params.get("new_name") or params.get("new_item_name")
    if new_name and new_name != item["name"]:
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="name",
                from_value=item["name"],
                to_value=new_name,
            )
        )
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine what to change")
    label = new_name or item["name"]
    return Plan(changes=changes, scope="items", summary=f"Updated '{label}'")


async def _plan_bulk_price(params: dict, location_id: str, menu: MenuClient, *, classifier_scope: str | None) -> Plan:
    change_pct = params.get("change_pct")
    change_abs = params.get("change_abs")
    if change_pct is None and change_abs is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the price change")
    items = await menu.list_all_items(location_id)
    category_hint = params.get("category_hint") or params.get("category")
    scope: Scope
    if category_hint:
        categories = await menu.list_categories(location_id)
        category = _require_match(category_hint, categories, "category")
        items = [item for item in items if item.get("categoryId") == category["id"]]
        scope = "category"
    elif _explicit_location_scope(params, classifier_scope):
        scope = "location"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine which prices to change — name a category, or say the whole menu",
        )
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No items found for that price change")
    changes: list[Change] = []
    for item in items:
        current = _item_price(item)
        if change_pct is not None:
            nxt = money(current * (Decimal("1") + Decimal(str(change_pct)) / Decimal("100")))
        else:
            nxt = money(current + money(change_abs or 0))
        nxt = max(money(0), nxt)
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="price",
                from_value=float(current),
                to_value=float(nxt),
            )
        )
    return Plan(changes=changes, scope=scope, summary=f"Updated prices for {len(changes)} item(s)")


async def _plan_toggle_availability(params: dict, location_id: str, menu: MenuClient) -> Plan:
    item = await _resolve_item(params, location_id, menu)
    in_stock = params.get("in_stock")
    if in_stock is None:
        available = params.get("available")
        in_stock = bool(available) if available is not None else not item["inStock"]
    return Plan(
        changes=[
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="inStock",
                from_value=item.get("inStock"),
                to_value=bool(in_stock),
            )
        ],
        scope="items",
        summary=f"Marked '{item['name']}' as {'in stock' if in_stock else 'out of stock'}",
    )


async def _plan_trash(params: dict, location_id: str, menu: MenuClient) -> Plan:
    item = await _resolve_item(params, location_id, menu)
    return Plan(
        changes=[
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="deleted",
                from_value=False,
                to_value=True,
            )
        ],
        scope="items",
        summary=f"Moved '{item['name']}' to trash",
    )


async def _plan_restore(params: dict, location_id: str, menu: MenuClient) -> Plan:
    item = await _resolve_trashed_item(params, location_id, menu)
    return Plan(
        changes=[
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="restored",
                from_value=False,
                to_value=True,
            )
        ],
        scope="items",
        summary=f"Restored '{item['name']}' from trash",
    )


async def _plan_permanent_delete(params: dict, location_id: str, menu: MenuClient) -> Plan:
    item = await _resolve_trashed_item(params, location_id, menu)
    return Plan(
        changes=[
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="permanentlyDeleted",
                from_value=False,
                to_value=True,
            )
        ],
        scope="items",
        summary=f"Permanently deleted '{item['name']}' — this cannot be undone",
    )


async def _plan_move_items(params: dict, location_id: str, menu: MenuClient) -> Plan:
    raw_items = params.get("item_hints") or params.get("items") or params.get("item_names") or params.get("item_hint")
    if isinstance(raw_items, str):
        raw_items = [s.strip() for s in raw_items.split(",") if s.strip()]
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which items to move")
    category_hint = params.get("category_hint") or params.get("category") or params.get("target_category")
    if not category_hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the target category")
    categories = await menu.list_categories(location_id)
    target = _require_match(category_hint, categories, "category")
    items = await menu.list_all_items(location_id)
    changes: list[Change] = []
    not_found: list[str] = []
    for hint in raw_items:
        try:
            item = _require_match(hint, items, "item")
        except HTTPException:
            not_found.append(hint)
            continue
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="categoryId",
                from_value=item.get("categoryId"),
                to_value=target["id"],
            )
        )
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": f"None of the items ({', '.join(raw_items)}) were found", "suggestions": []},
        )
    message = f"Moved {', '.join(c.name for c in changes)} to '{target['name']}'"
    if not_found:
        message += f" (couldn't find: {', '.join(not_found)})"
    return Plan(changes=changes, scope="items", summary=message)


async def _plan_printer_route(params: dict, location_id: str, menu: MenuClient, printing: PrintingClient) -> Plan:
    printer_hint = params.get("printer_hint") or params.get("printer") or params.get("printer_name")
    if not printer_hint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which printer to route to"
        )
    printers = await printing.list_printers(location_id)
    try:
        printer_idx = match_index(printer_hint, printers, keys=("name", "type"))
    except MatchError as exc:
        raise _http_match(exc, "printer") from exc
    if printer_idx is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which printer")
    target_printer = printers[printer_idx]
    items = await menu.list_all_items(location_id)
    targets: list[dict] = []
    scope: Scope = "items"
    category_hint = params.get("category_hint") or params.get("category")
    if category_hint:
        categories = await menu.list_categories(location_id)
        target_category = _require_match(category_hint, categories, "category")
        targets = [i for i in items if i.get("categoryId") == target_category["id"]]
        scope = "category"
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No items found in category '{target_category['name']}'"
            )
    else:
        raw_items = (
            params.get("item_hints") or params.get("items") or params.get("item_hint") or params.get("item_name")
        )
        if isinstance(raw_items, str):
            raw_items = [s.strip() for s in raw_items.split(",") if s.strip()]
        if not raw_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item(s) to route"
            )
        for hint in raw_items:
            targets.append(_require_match(hint, items, "item"))
    replace_existing = bool(params.get("replace_existing", not params.get("add_only", False)))
    existing_routes = await printing.list_routes(location_id) if replace_existing else []
    changes: list[Change] = []
    for item in targets:
        delete_ids = [
            route["id"]
            for route in existing_routes
            if route["itemId"] == item["id"] and route["printerId"] != target_printer["id"]
        ]
        current = [route["printerId"] for route in existing_routes if route["itemId"] == item["id"]]
        changes.append(
            Change(
                entity="item",
                id=item["id"],
                name=item["name"],
                field="printerRoute",
                from_value=current,
                to_value=target_printer["id"],
                extra={"deleteRouteIds": delete_ids, "printerName": target_printer["name"]},
            )
        )
    names = ", ".join(change.name for change in changes)
    return Plan(
        changes=changes,
        scope=scope,
        summary=f"Routed {names} to '{target_printer['name']}'",
    )


async def _plan_reorganize_categories(params: dict, location_id: str, menu: MenuClient) -> Plan:
    raw_tops = (
        params.get("new_top_categories")
        or params.get("top_categories")
        or params.get("main_categories")
        or params.get("categories")
    )
    if isinstance(raw_tops, str):
        raw_tops = [s.strip() for s in raw_tops.split(",") if s.strip()]
    if not raw_tops:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the new top-level category names"
        )
    existing = await menu.list_categories(location_id)
    existing_top = [c for c in existing if c.get("parentId") is None]
    name_to_cat = {c["name"]: c for c in existing_top}
    changes: list[Change] = []
    new_top_cats: list[dict] = []
    created_names: list[str] = []
    for name in raw_tops:
        cat = name_to_cat.get(name)
        if not cat:
            changes.append(
                Change(entity="category", id=None, name=name, field="create", from_value=None, to_value=name)
            )
            created_names.append(name)
            cat = {"id": None, "name": name}
        new_top_cats.append(cat)
    new_top_ids = {c["id"] for c in new_top_cats if c.get("id")}
    to_reassign = [c for c in existing_top if c["id"] not in new_top_ids]
    if to_reassign:
        if not settings.ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service not configured (set ANTHROPIC_API_KEY)",
            )
        system = MENU_REORG_SYSTEM_PROMPT.format(
            new_top_categories=", ".join(c["name"] for c in new_top_cats),
            existing_categories=", ".join(c["name"] for c in to_reassign),
        )
        message = await create_message(
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": "Assign each existing category to a top-level category."}],
        )
        plan = parse_json_reply(message)
        assignments: dict = plan.get("assignments", {})
        named_targets = [c for c in new_top_cats if c.get("id")]
        for cat in to_reassign:
            target_name = assignments.get(cat["name"])
            try:
                target = (
                    _require_match(target_name, named_targets or new_top_cats, "category")
                    if target_name
                    else (named_targets[0] if named_targets else new_top_cats[0])
                )
            except HTTPException:
                target = named_targets[0] if named_targets else new_top_cats[0]
            if not target.get("id"):
                continue
            changes.append(
                Change(
                    entity="category",
                    id=cat["id"],
                    name=cat["name"],
                    field="parentId",
                    from_value=cat.get("parentId"),
                    to_value=target["id"],
                )
            )
    if created_names and not to_reassign:
        summary = f"Created {len(created_names)} top-level categories: {', '.join(created_names)}"
    elif created_names:
        summary = (
            f"Created {len(created_names)} new categories ({', '.join(created_names)}) "
            f"and reorganized existing categories under them"
        )
    else:
        summary = f"Reorganized existing categories under {', '.join(c['name'] for c in new_top_cats)}"
    return Plan(changes=changes, scope="items", summary=summary)


async def _resolve_item(params: dict, location_id: str, menu: MenuClient):
    hint = params.get("name") or params.get("item_hint") or params.get("item_name")
    if not hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item to update")
    items = await menu.list_all_items(location_id)
    return _require_match(hint, items, "item")


async def _resolve_trashed_item(params: dict, location_id: str, menu: MenuClient):
    hint = params.get("name") or params.get("item_hint") or params.get("item_name")
    if not hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item to update")
    items = await menu.list_trashed_items(location_id)
    try:
        return _require_match(hint, items, "trashed item")
    except HTTPException as exc:
        if exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trashed item matching '{hint}' was found",
            ) from exc
        raise

"""Executes confirmed AI commands via HTTP calls to services/catalog — ai owns no local
DB/models (see app/modules/ai/services/menu_client.py and docs/microservices-plan.md §4)."""

import anthropic
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.ai.services.client import create_message, parse_json_reply
from app.modules.ai.services.menu_client import MenuClient, PrintingClient
from app.modules.ai.services.prompts import MENU_REORG_SYSTEM_PROMPT


def fuzzy_match(hint: str | None, names: list[str]) -> int | None:
    """Return the index of the best case-insensitive match for `hint` among `names`, or None if nothing matches."""
    if not hint:
        return None
    hint_lower = hint.strip().lower()
    for i, name in enumerate(names):
        if name.lower() == hint_lower:
            return i
    for i, name in enumerate(names):
        if hint_lower in name.lower() or name.lower() in hint_lower:
            return i
    return None


def _category_and_descendant_ids(categories: list[dict], root_id: str) -> set[str]:
    """`root_id` plus every category nested under it at any depth — a bulk action on a
    parent category (e.g. "Drinks") should also reach items filed under its subcategories
    (e.g. "Soft Drinks"), not just items whose categoryId is the parent's own id directly."""
    children_by_parent: dict[str | None, list[str]] = {}
    for c in categories:
        children_by_parent.setdefault(c.get("parentId"), []).append(c["id"])
    ids = {root_id}
    frontier = [root_id]
    while frontier:
        frontier = [cid for parent in frontier for cid in children_by_parent.get(parent, [])]
        ids.update(frontier)
    return ids


async def dispatch_intent(
    intent: str, params: dict, location_id: str, menu: MenuClient, printing: PrintingClient
) -> str:
    """Execute a confirmed AI command. Raises HTTPException for anything that can't be resolved or automated —
    a confirmed action must either really happen or clearly fail, never silently report fake success."""
    if intent == "printer.route":
        return await _dispatch_printer_route(params, location_id, menu, printing)

    if intent == "menu.create_category":
        name = params.get("name") or params.get("category_name")
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the category name")
        parent_id = None
        parent_hint = params.get("parent_name") or params.get("parent") or params.get("parent_category")
        if parent_hint:
            categories = await menu.list_categories(location_id)
            idx = fuzzy_match(parent_hint, [c["name"] for c in categories])
            if idx is not None:
                parent_id = categories[idx]["id"]
        cat = await menu.create_category(location_id=location_id, name=name, parent_id=parent_id)
        return f"Created category '{cat['name']}'" + (" as a subcategory" if parent_id else "")

    if intent == "menu.reorganize_categories":
        return await _dispatch_reorganize_categories(params, location_id, menu)

    if intent == "menu.move_items_to_category":
        return await _dispatch_move_items_to_category(params, location_id, menu)

    if intent == "menu.create_item":
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
        idx = fuzzy_match(category_hint, [c["name"] for c in categories])
        category = categories[idx] if idx is not None else categories[0]
        item = await menu.create_item(category_id=category["id"], name=name, price=float(price))
        return f"Created '{item['name']}' ({item['price']:.2f}) in '{category['name']}'"

    if intent == "menu.update_item":
        item = await _resolve_item(params, location_id, menu)
        fields: dict = {}
        if "price" in params or "new_price" in params:
            # guarded by the `in` check above, so the value is never actually None here
            fields["price"] = float(params.get("price", params.get("new_price")))  # type: ignore[arg-type]
        if "description" in params:
            fields["description"] = params["description"]
        # a rename needs a *different* key than the identifying hint _resolve_item already
        # consumed above, since "the item to find" and "its new name" are never the same value
        new_name = params.get("new_name") or params.get("new_item_name")
        if new_name and new_name != item["name"]:
            fields["name"] = new_name
        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine what to change")
        updated = await menu.update_item(item["id"], **fields)
        return f"Updated '{updated['name']}'"

    if intent == "menu.bulk_price_change":
        change_pct = params.get("change_pct")
        change_abs = params.get("change_abs")
        if change_pct is None and change_abs is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the price change")
        category_id = None
        category_hint = params.get("category_hint") or params.get("category")
        if category_hint:
            categories = await menu.list_categories(location_id)
            idx = fuzzy_match(category_hint, [c["name"] for c in categories])
            if idx is not None:
                category_id = categories[idx]["id"]
        count = await menu.bulk_price_update(
            location_id=location_id,
            category_id=category_id,
            change_pct=float(change_pct) if change_pct is not None else None,
            change_abs=float(change_abs) if change_abs is not None else None,
        )
        return f"Updated prices for {count} item(s)"

    if intent == "menu.toggle_availability":
        item = await _resolve_item(params, location_id, menu)
        in_stock = params.get("in_stock")
        if in_stock is None:
            available = params.get("available")
            in_stock = bool(available) if available is not None else not item["inStock"]
        updated = await menu.set_stock(item["id"], bool(in_stock))
        return f"Marked '{updated['name']}' as {'in stock' if updated['inStock'] else 'out of stock'}"

    if intent == "menu.move_to_trash":
        return await _dispatch_move_to_trash(params, location_id, menu)

    if intent == "menu.restore_item":
        item = await _resolve_trashed_item(params, location_id, menu)
        restored = await menu.restore_item(item["id"])
        return f"Restored '{restored['name']}' from trash"

    if intent == "menu.permanently_delete_item":
        item = await _resolve_trashed_item(params, location_id, menu)
        await menu.permanently_delete_item(item["id"])
        return f"Permanently deleted '{item['name']}' — this cannot be undone"

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"'{intent}' isn't automated yet — please make this change manually",
    )


async def _dispatch_printer_route(params: dict, location_id: str, menu: MenuClient, printing: PrintingClient) -> str:
    printer_hint = params.get("printer_hint") or params.get("printer") or params.get("printer_name")
    if not printer_hint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which printer to route to"
        )

    printers = await printing.list_printers(location_id)
    printer_idx = fuzzy_match(printer_hint, [p["name"] for p in printers])
    if printer_idx is None:
        # Fall back to matching the printer TYPE (e.g. "kitchen", "receipt", "label") when no
        # printer is named that, since users often refer to printers by role, not name.
        printer_idx = fuzzy_match(printer_hint, [p["type"] for p in printers])
    if printer_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No printer matching '{printer_hint}' was found"
        )
    target_printer = printers[printer_idx]

    items = await menu.list_all_items(location_id)
    targets: list[dict] = []

    category_hint = params.get("category_hint") or params.get("category")
    if category_hint:
        categories = await menu.list_categories(location_id)
        cat_idx = fuzzy_match(category_hint, [c["name"] for c in categories])
        if cat_idx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No category matching '{category_hint}' was found"
            )
        target_category = categories[cat_idx]
        targets = [i for i in items if i.get("categoryId") == target_category["id"]]
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
        not_found = []
        for hint in raw_items:
            idx = fuzzy_match(hint, [i["name"] for i in items])
            if idx is None:
                not_found.append(hint)
            else:
                targets.append(items[idx])
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"None of the items ({', '.join(raw_items)}) were found"
            )

    # "instead"/"only" phrasing implies replacing existing routes, not adding a second one —
    # default to replace unless the request explicitly asked to add an additional route.
    replace_existing = bool(params.get("replace_existing", not params.get("add_only", False)))
    existing_routes = await printing.list_routes(location_id) if replace_existing else []

    routed_names = []
    for item in targets:
        if replace_existing:
            for route in existing_routes:
                if route["itemId"] == item["id"] and route["printerId"] != target_printer["id"]:
                    await printing.delete_route(route["id"])
        await printing.add_route(target_printer["id"], item["id"])
        routed_names.append(item["name"])

    return f"Routed {', '.join(routed_names)} to '{target_printer['name']}'"


async def _resolve_item(params: dict, location_id: str, menu: MenuClient):
    hint = params.get("name") or params.get("item_hint") or params.get("item_name")
    if not hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item to update")
    items = await menu.list_all_items(location_id)
    idx = fuzzy_match(hint, [i["name"] for i in items])
    if idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No item matching '{hint}' was found")
    return items[idx]


async def _resolve_trashed_item(params: dict, location_id: str, menu: MenuClient):
    """Like `_resolve_item`, but searches the trash — `list_all_items` excludes trashed items
    by default, so restore/permanent-delete must look up the target there instead."""
    hint = params.get("name") or params.get("item_hint") or params.get("item_name")
    if not hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item to update")
    items = await menu.list_trashed_items(location_id)
    idx = fuzzy_match(hint, [i["name"] for i in items])
    if idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No trashed item matching '{hint}' was found"
        )
    return items[idx]


async def _dispatch_move_to_trash(params: dict, location_id: str, menu: MenuClient) -> str:
    """Supports three shapes, mirroring `_dispatch_printer_route`: a whole category
    (category_hint — trash every item in it), an explicit list of items (item_hints),
    or a single item (falls back to `_resolve_item`)."""
    category_hint = params.get("category_hint") or params.get("category")
    if category_hint:
        categories = await menu.list_categories(location_id)
        cat_idx = fuzzy_match(category_hint, [c["name"] for c in categories])
        if cat_idx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No category matching '{category_hint}' was found"
            )
        target_category = categories[cat_idx]
        category_ids = _category_and_descendant_ids(categories, target_category["id"])
        items = await menu.list_all_items(location_id)
        targets = [i for i in items if i.get("categoryId") in category_ids]
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No items found in category '{target_category['name']}'"
            )
        for item in targets:
            await menu.move_to_trash(item["id"])
        return f"Moved {len(targets)} item(s) to trash from '{target_category['name']}'"

    raw_items = params.get("item_hints") or params.get("items") or params.get("item_names")
    if isinstance(raw_items, str):
        raw_items = [s.strip() for s in raw_items.split(",") if s.strip()]
    if raw_items:
        items = await menu.list_all_items(location_id)
        trashed, not_found = [], []
        for hint in raw_items:
            idx = fuzzy_match(hint, [i["name"] for i in items])
            if idx is None:
                not_found.append(hint)
                continue
            item = items[idx]
            await menu.move_to_trash(item["id"])
            trashed.append(item["name"])
        if not trashed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"None of the items ({', '.join(raw_items)}) were found"
            )
        message = f"Moved {', '.join(trashed)} to trash"
        if not_found:
            message += f" (couldn't find: {', '.join(not_found)})"
        return message

    item = await _resolve_item(params, location_id, menu)
    await menu.move_to_trash(item["id"])
    return f"Moved '{item['name']}' to trash"


async def _dispatch_move_items_to_category(params: dict, location_id: str, menu: MenuClient) -> str:
    raw_items = params.get("item_hints") or params.get("items") or params.get("item_names") or params.get("item_hint")
    if isinstance(raw_items, str):
        raw_items = [s.strip() for s in raw_items.split(",") if s.strip()]
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which items to move")

    category_hint = params.get("category_hint") or params.get("category") or params.get("target_category")
    if not category_hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the target category")

    categories = await menu.list_categories(location_id)
    cat_idx = fuzzy_match(category_hint, [c["name"] for c in categories])
    if cat_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No category matching '{category_hint}' was found"
        )
    target = categories[cat_idx]

    items = await menu.list_all_items(location_id)
    moved, not_found = [], []
    for hint in raw_items:
        idx = fuzzy_match(hint, [i["name"] for i in items])
        if idx is None:
            not_found.append(hint)
            continue
        item = items[idx]
        await menu.update_item(item["id"], category_id=target["id"])
        moved.append(item["name"])

    if not moved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"None of the items ({', '.join(raw_items)}) were found"
        )

    message = f"Moved {', '.join(moved)} to '{target['name']}'"
    if not_found:
        message += f" (couldn't find: {', '.join(not_found)})"
    return message


async def _dispatch_reorganize_categories(params: dict, location_id: str, menu: MenuClient) -> str:
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

    created_names = []
    new_top_cats = []
    for name in raw_tops:
        cat = name_to_cat.get(name)
        if not cat:
            cat = await menu.create_category(location_id=location_id, name=name, sort_order=len(existing))
            name_to_cat[name] = cat
            created_names.append(cat["name"])
        new_top_cats.append(cat)

    new_top_ids = {c["id"] for c in new_top_cats}
    to_reassign = [c for c in existing_top if c["id"] not in new_top_ids]

    if not to_reassign:
        return f"Created {len(created_names)} top-level categories: {', '.join(created_names)}"

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_REORG_SYSTEM_PROMPT.format(
        new_top_categories=", ".join(c["name"] for c in new_top_cats),
        existing_categories=", ".join(c["name"] for c in to_reassign),
    )
    message = await create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": "Assign each existing category to a top-level category."}],
    )
    plan = parse_json_reply(message)
    assignments: dict = plan.get("assignments", {})

    reassigned = 0
    for cat in to_reassign:
        target_name = assignments.get(cat["name"])
        idx = fuzzy_match(target_name, [c["name"] for c in new_top_cats]) if target_name else None
        target = new_top_cats[idx] if idx is not None else new_top_cats[0]
        await menu.update_category(cat["id"], parent_id=target["id"])
        reassigned += 1

    if created_names:
        return (
            f"Created {len(created_names)} new categories ({', '.join(created_names)}) "
            f"and reorganized {reassigned} existing categories under them"
        )
    return f"Reorganized {reassigned} existing categories under {', '.join(c['name'] for c in new_top_cats)}"

"""AI command endpoint — intent classification, action preview, and menu import."""

import asyncio
import base64
import io
import json
import uuid
import zipfile

import anthropic
from defusedxml import ElementTree
from defusedxml import common as defused_common
from fastapi import Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.api.v1.router_base import APIRouter
from app.core.config import settings
from app.core.security import decode_token
from app.db.models import Location, MenuCategory, MenuItem, Printer, PrinterRoute, User
from app.db.session import get_db
from app.schemas.base import BaseSchema
from app.schemas.menu import BulkPriceUpdate, MenuCategoryCreate, MenuCategoryUpdate, MenuItemCreate, MenuItemUpdate
from app.services.menu import MenuService

router = APIRouter()
bearer = HTTPBearer()

# All supported intents — sent as context to Haiku for classification
SUPPORTED_INTENTS = [
    "menu.create_item",
    "menu.update_item",
    "menu.bulk_price_change",
    "menu.toggle_availability",
    "menu.create_category",
    "menu.reorganize_categories",
    "menu.move_items_to_category",
    "menu.create_modifier_group",
    "printer.route",
    "printer.troubleshoot",
    "report.query",
    "staff.add_user",
    "staff.set_permissions",
    "inventory.set_threshold",
    "settings.business",
    "help.general",
]

INTENT_SYSTEM_PROMPT = """You are the intent classifier for SmartServe, a restaurant POS system.
Classify the user's request into exactly one of these intents and extract parameters.

Intents: {intents}

Return ONLY valid JSON in this exact format:
{{
  "intent": "<intent_name>",
  "confidence": <0.0-1.0>,
  "params": {{<extracted parameters as key-value pairs>}},
  "preview": "<one sentence describing what will happen in Hebrew or English matching the user's language>"
}}

Examples:
- "Add margherita pizza for 58 NIS" → intent: menu.create_item, params: {{name: "Margherita Pizza", price: 58, currency: "ILS"}}
- "הגדל את כל מחירי הפסטה ב-10%" → intent: menu.bulk_price_change, params: {{category_hint: "פסטה", change_pct: 10}}
- "Send burgers to the kitchen printer" → intent: printer.route, params: {{item_hint: "burger", printer_hint: "kitchen"}}
- "Reorganize my menu into Food and Drinks main sections" → intent: menu.reorganize_categories,
  params: {{new_top_categories: ["Food", "Drinks"]}}
- "Move Cola and Lemonade into the Soft Drinks category" → intent: menu.move_items_to_category,
  params: {{item_hints: ["Cola", "Lemonade"], category_hint: "Soft Drinks"}}
"""


class CommandRequest(BaseSchema):
    message: str
    context: dict


class ConfirmRequest(BaseSchema):
    execution_id: str


# In-memory pending executions store (replace with Redis in step/02)
_pending: dict[str, dict] = {}


def _parse_json_reply(message: anthropic.types.Message) -> dict:
    """Claude occasionally wraps JSON in ```json fences despite instructions — strip and retry."""
    text = message.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(stripped)


def _parse_menu_import_reply(message: anthropic.types.Message) -> dict:
    """Like _parse_json_reply, but turns a truncated/invalid reply into a clean HTTP error
    instead of an unhandled 500 (large menus can exceed max_tokens and cut the JSON off mid-item)."""
    try:
        return _parse_json_reply(message)
    except (json.JSONDecodeError, IndexError) as exc:
        if message.stop_reason == "max_tokens":
            detail = "The menu was too large for the AI to process in one go — try uploading fewer items at a time"
        else:
            detail = "AI returned an invalid response, please try again"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc


async def _create_message(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Call the Anthropic API off the event loop, turning SDK errors into clean HTTP responses."""
    try:
        return await asyncio.to_thread(client.messages.create, **kwargs)
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="AI service is busy, please try again shortly"
        ) from exc
    except anthropic.APIStatusError as exc:
        message = exc.body.get("error", {}).get("message") if isinstance(exc.body, dict) else str(exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI service error: {message}") from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI service error: {exc}") from exc


@router.post("/command")
async def ai_command(
    body: CommandRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    decode_token(credentials.credentials)  # validates JWT

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system = INTENT_SYSTEM_PROMPT.format(intents=", ".join(SUPPORTED_INTENTS))

    message = await _create_message(
        client,
        model=settings.AI_INTENT_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": body.message}],
    )

    try:
        result = _parse_json_reply(message)
    except json.JSONDecodeError, IndexError, KeyError:
        # Fallback to Sonnet when Haiku produces malformed output
        message = await _create_message(
            client,
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = _parse_json_reply(message)

    confidence: float = result.get("confidence", 0)

    # If confidence is low, use Sonnet for a more careful classification
    if confidence < settings.AI_INTENT_CONFIDENCE_THRESHOLD:
        message = await _create_message(
            client,
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = _parse_json_reply(message)

    execution_id = str(uuid.uuid4())
    _pending[execution_id] = {
        "intent": result.get("intent"),
        "params": result.get("params", {}),
        "context": body.context,
    }

    return {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "params": result.get("params", {}),
        "preview": result.get("preview", ""),
        "requiresConfirmation": True,
        "executionId": execution_id,
    }


MENU_REORG_SYSTEM_PROMPT = """You help reorganize a restaurant's menu categories into new top-level sections.

New top-level categories: {new_top_categories}
Existing categories that need to be assigned to one of the new top-level categories: {existing_categories}

Assign every existing category to exactly one of the new top-level categories, based on what best fits its name
(e.g. a "Cocktails" category fits under a "Drinks" top-level category).

Return ONLY valid JSON in this exact format:
{{"assignments": {{"<existing category name>": "<new top-level category name>", ...}}}}
"""


def _fuzzy_match(hint: str | None, names: list[str]) -> int | None:
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


async def _dispatch_intent(intent: str, params: dict, location_id: str, db: AsyncSession) -> str:
    """Execute a confirmed AI command. Raises HTTPException for anything that can't be resolved or automated —
    a confirmed action must either really happen or clearly fail, never silently report fake success."""
    menu_service = MenuService(db)

    if intent == "menu.create_category":
        name = params.get("name") or params.get("category_name")
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the category name")
        parent_id = None
        parent_hint = params.get("parent_name") or params.get("parent") or params.get("parent_category")
        if parent_hint:
            categories = await menu_service.list_categories(location_id)
            idx = _fuzzy_match(parent_hint, [c.name for c in categories])
            if idx is not None:
                parent_id = categories[idx].id
        cat = await menu_service.create_category(
            MenuCategoryCreate(location_id=location_id, name=name, parent_id=parent_id)
        )
        return f"Created category '{cat.name}'" + (" as a subcategory" if parent_id else "")

    if intent == "menu.reorganize_categories":
        return await _dispatch_reorganize_categories(params, location_id, menu_service)

    if intent == "menu.move_items_to_category":
        return await _dispatch_move_items_to_category(params, location_id, menu_service)

    if intent == "menu.create_item":
        name = params.get("name")
        price = params.get("price")
        if not name or price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the item name and price"
            )
        categories = await menu_service.list_categories(location_id)
        if not categories:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No categories exist yet for this item")
        category_hint = params.get("category_hint") or params.get("category")
        idx = _fuzzy_match(category_hint, [c.name for c in categories])
        category = categories[idx] if idx is not None else categories[0]
        item = await menu_service.create_item(MenuItemCreate(category_id=category.id, name=name, price=float(price)))
        return f"Created '{item.name}' ({item.price:.2f}) in '{category.name}'"

    if intent == "menu.update_item":
        item = await _resolve_item(params, location_id, menu_service)
        fields: dict = {}
        if "price" in params or "new_price" in params:
            fields["price"] = float(params.get("price", params.get("new_price")))
        if "description" in params:
            fields["description"] = params["description"]
        if "name" in params and params["name"] != item.name:
            fields["name"] = params["name"]
        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine what to change")
        updated = await menu_service.update_item(item.id, MenuItemUpdate(**fields))
        return f"Updated '{updated.name}'"

    if intent == "menu.bulk_price_change":
        change_pct = params.get("change_pct")
        change_abs = params.get("change_abs")
        if change_pct is None and change_abs is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the price change")
        category_id = None
        category_hint = params.get("category_hint") or params.get("category")
        if category_hint:
            categories = await menu_service.list_categories(location_id)
            idx = _fuzzy_match(category_hint, [c.name for c in categories])
            if idx is not None:
                category_id = categories[idx].id
        count = await menu_service.bulk_price_update(
            BulkPriceUpdate(
                location_id=location_id,
                category_id=category_id,
                change_pct=float(change_pct) if change_pct is not None else None,
                change_abs=float(change_abs) if change_abs is not None else None,
            )
        )
        return f"Updated prices for {count} item(s)"

    if intent == "menu.toggle_availability":
        item = await _resolve_item(params, location_id, menu_service)
        in_stock = params.get("in_stock")
        if in_stock is None:
            available = params.get("available")
            in_stock = bool(available) if available is not None else not item.in_stock
        updated = await menu_service.set_stock(item.id, bool(in_stock))
        return f"Marked '{updated.name}' as {'in stock' if updated.in_stock else 'out of stock'}"

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"'{intent}' isn't automated yet — please make this change manually",
    )


async def _resolve_item(params: dict, location_id: str, menu_service: MenuService):
    hint = params.get("name") or params.get("item_hint") or params.get("item_name")
    if not hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which item to update")
    items = await menu_service.list_all_items(location_id)
    idx = _fuzzy_match(hint, [i.name for i in items])
    if idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No item matching '{hint}' was found")
    return items[idx]


async def _dispatch_move_items_to_category(params: dict, location_id: str, menu_service: MenuService) -> str:
    raw_items = params.get("item_hints") or params.get("items") or params.get("item_names") or params.get("item_hint")
    if isinstance(raw_items, str):
        raw_items = [s.strip() for s in raw_items.split(",") if s.strip()]
    if not raw_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which items to move")

    category_hint = params.get("category_hint") or params.get("category") or params.get("target_category")
    if not category_hint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the target category")

    categories = await menu_service.list_categories(location_id)
    cat_idx = _fuzzy_match(category_hint, [c.name for c in categories])
    if cat_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No category matching '{category_hint}' was found"
        )
    target = categories[cat_idx]

    items = await menu_service.list_all_items(location_id)
    moved, not_found = [], []
    for hint in raw_items:
        idx = _fuzzy_match(hint, [i.name for i in items])
        if idx is None:
            not_found.append(hint)
            continue
        item = items[idx]
        await menu_service.update_item(item.id, MenuItemUpdate(category_id=target.id))
        moved.append(item.name)

    if not moved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"None of the items ({', '.join(raw_items)}) were found"
        )

    message = f"Moved {', '.join(moved)} to '{target.name}'"
    if not_found:
        message += f" (couldn't find: {', '.join(not_found)})"
    return message


async def _dispatch_reorganize_categories(params: dict, location_id: str, menu_service: MenuService) -> str:
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

    existing = await menu_service.list_categories(location_id)
    existing_top = [c for c in existing if c.parent_id is None]
    name_to_cat = {c.name: c for c in existing_top}

    created_names = []
    new_top_cats = []
    for name in raw_tops:
        cat = name_to_cat.get(name)
        if not cat:
            cat = await menu_service.create_category(
                MenuCategoryCreate(location_id=location_id, name=name, sort_order=len(existing))
            )
            name_to_cat[name] = cat
            created_names.append(cat.name)
        new_top_cats.append(cat)

    new_top_ids = {c.id for c in new_top_cats}
    to_reassign = [c for c in existing_top if c.id not in new_top_ids]

    if not to_reassign:
        return f"Created {len(created_names)} top-level categories: {', '.join(created_names)}"

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_REORG_SYSTEM_PROMPT.format(
        new_top_categories=", ".join(c.name for c in new_top_cats),
        existing_categories=", ".join(c.name for c in to_reassign),
    )
    message = await _create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": "Assign each existing category to a top-level category."}],
    )
    plan = _parse_json_reply(message)
    assignments: dict = plan.get("assignments", {})

    reassigned = 0
    for cat in to_reassign:
        target_name = assignments.get(cat.name)
        idx = _fuzzy_match(target_name, [c.name for c in new_top_cats]) if target_name else None
        target = new_top_cats[idx] if idx is not None else new_top_cats[0]
        await menu_service.update_category(cat.id, MenuCategoryUpdate(parent_id=target.id))
        reassigned += 1

    if created_names:
        return f"Created {len(created_names)} new categories ({', '.join(created_names)}) and reorganized {reassigned} existing categories under them"
    return f"Reorganized {reassigned} existing categories under {', '.join(c.name for c in new_top_cats)}"


@router.post("/confirm")
async def ai_confirm(
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    pending = _pending.pop(body.execution_id, None)
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found or already confirmed")

    intent = pending["intent"]
    params = pending.get("params") or {}
    context = pending.get("context") or {}

    location_id = context.get("locationId")
    if not location_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing location context")
    await _get_owned_location(db, location_id, user)

    message = await _dispatch_intent(intent, params, location_id, db)

    return {"success": True, "message": message}


# ─── Menu import (upload a menu photo/PDF/sheet, AI extracts + organizes it) ──

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
SUPPORTED_TEXT_TYPES = {"text/plain", "text/csv"}
DOCX_MIME_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB
DOCX_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

MENU_IMPORT_SYSTEM_PROMPT = """You are a menu-import assistant for SmartServe, a restaurant POS system.
You are shown a photo, screenshot, PDF, or text/spreadsheet export of a restaurant's menu (English or Hebrew).

Extract every distinct menu item you can find: name, an optional short description, and its price.
For each item, suggest:
- "category": a short category name (use one of the business's EXISTING categories below when it clearly fits,
  otherwise propose a new, sensible category name)
- "printerTypes": an array of printer types this item's tickets should print to — each one of "kitchen",
  "receipt", "label". Most items need to print to MORE THAN ONE printer at once (e.g. a burger prints a ticket
  to the kitchen printer AND a copy to the receipt printer); include every printer type that makes sense, not
  just one. Use an empty array only if you are not confident. Pick based on the business's EXISTING printers below.

This business's existing categories: {categories}
This business's existing printers (name/type): {printers}

Return ONLY valid JSON, no markdown fences, in exactly this format:
{{
  "items": [
    {{"name": "...", "nameHe": null, "description": null, "price": 42.0, "currency": "ILS",
      "category": "...", "printerTypes": ["kitchen", "receipt"]}}
  ],
  "message": "<a short reply to the user, in the language they used>",
  "needsClarification": <true|false>
}}

Set "needsClarification" to true and use "message" to ask a specific, single follow-up question when: prices are
missing or illegible, a group of items has no obvious category, or printer routing for an item is genuinely
ambiguous between two existing printers of the same type. Otherwise set it to false and put a brief summary
(e.g. item count and categories found) in "message". Keep conversing with the user turn-by-turn until every item
has a clear category and, where possible, printer assignments — incorporate their replies to refine "items".
"""

_menu_import_sessions: dict[str, dict] = {}


class MenuImportMessageRequest(BaseSchema):
    session_id: str
    message: str


class MenuImportApplyRequest(BaseSchema):
    session_id: str
    items: list[dict] | None = None  # optional final edited list; falls back to the session's current items


async def _get_owned_location(db: AsyncSession, location_id: str, user: User) -> Location:
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location or location.business_id != user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


async def _fetch_menu_context(db: AsyncSession, location_id: str) -> tuple[str, str]:
    cats = await db.execute(select(MenuCategory.name).where(MenuCategory.location_id == location_id))
    printers = await db.execute(select(Printer.name, Printer.type).where(Printer.location_id == location_id))
    cat_names = ", ".join(c for (c,) in cats.all()) or "(none yet)"
    printer_list = ", ".join(f"{name} ({ptype})" for name, ptype in printers.all()) or "(none yet)"
    return cat_names, printer_list


def _extract_docx_text(content: bytes) -> str:
    """Pull plain text out of a .docx's word/document.xml — avoids a python-docx dependency."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    lines = []
    for para in root.iter(f"{DOCX_WORD_NS}p"):
        line = "".join(node.text or "" for node in para.iter(f"{DOCX_WORD_NS}t"))
        lines.append(line)
    return "\n".join(lines)


def _build_content_block(content: bytes, content_type: str, filename: str) -> dict:
    lower_name = filename.lower()
    if content_type in SUPPORTED_IMAGE_TYPES:
        media_type = "image/jpeg" if content_type == "image/jpg" else content_type
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(content).decode()},
        }
    if content_type == "application/pdf" or lower_name.endswith(".pdf"):
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(content).decode()},
        }
    if content_type in SUPPORTED_TEXT_TYPES or lower_name.endswith((".txt", ".csv")):
        text = content.decode("utf-8", errors="ignore")
        return {"type": "text", "text": f"Menu file ({filename}):\n\n{text}"}
    if content_type in DOCX_MIME_TYPES or lower_name.endswith(".docx"):
        try:
            text = _extract_docx_text(content)
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, defused_common.DefusedXmlException) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read this .docx file"
            ) from exc
        return {"type": "text", "text": f"Menu file ({filename}):\n\n{text}"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Please upload an image (PNG/JPEG/WEBP), a PDF, a Word (.docx) file, or a text/CSV file.",
    )


@router.post("/menu-import")
async def menu_import_start(
    location_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    location = await _get_owned_location(db, location_id, user)

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 15MB)")

    block = _build_content_block(content, file.content_type or "", file.filename or "upload")
    categories, printers = await _fetch_menu_context(db, location.id)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_IMPORT_SYSTEM_PROMPT.format(categories=categories, printers=printers)
    user_content = [block, {"type": "text", "text": "Extract the menu items from this file."}]

    message = await _create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    result = _parse_menu_import_reply(message)

    session_id = str(uuid.uuid4())
    _menu_import_sessions[session_id] = {
        "business_id": user.business_id,
        "location_id": location.id,
        "items": result.get("items", []),
        "history": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": json.dumps(result)},
        ],
    }

    return {
        "sessionId": session_id,
        "items": result.get("items", []),
        "message": result.get("message", ""),
        "needsClarification": result.get("needsClarification", False),
    }


@router.post("/menu-import/message")
async def menu_import_message(
    body: MenuImportMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    session = _menu_import_sessions.get(body.session_id)
    if not session or session["business_id"] != user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session not found")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    categories, printers = await _fetch_menu_context(db, session["location_id"])
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_IMPORT_SYSTEM_PROMPT.format(categories=categories, printers=printers)

    history = [*session["history"], {"role": "user", "content": body.message}]

    message = await _create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=8192,
        system=system,
        messages=history,
    )
    result = _parse_menu_import_reply(message)

    session["items"] = result.get("items", session["items"])
    session["history"] = [*history, {"role": "assistant", "content": json.dumps(result)}]

    return {
        "sessionId": body.session_id,
        "items": session["items"],
        "message": result.get("message", ""),
        "needsClarification": result.get("needsClarification", False),
    }


@router.post("/menu-import/apply")
async def menu_import_apply(
    body: MenuImportApplyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    session = _menu_import_sessions.get(body.session_id)
    if not session or session["business_id"] != user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session not found")

    location_id = session["location_id"]
    items = body.items if body.items is not None else session["items"]

    existing_cats = await db.execute(select(MenuCategory).where(MenuCategory.location_id == location_id))
    cat_by_name = {c.name.strip().lower(): c for c in existing_cats.scalars().all()}
    existing_printers = await db.execute(select(Printer).where(Printer.location_id == location_id))
    printer_by_type: dict[str, Printer] = {}
    for p in existing_printers.scalars().all():
        printer_by_type.setdefault(p.type, p)

    categories_created = 0
    items_created = 0
    routes_created = 0
    unrouted: list[str] = []
    next_sort_order = len(cat_by_name)

    for raw in items:
        name = str(raw.get("name") or "").strip()
        if not name:
            continue

        category_name = str(raw.get("category") or "Uncategorized").strip()
        key = category_name.lower()
        category = cat_by_name.get(key)
        if not category:
            category = MenuCategory(location_id=location_id, name=category_name, sort_order=next_sort_order)
            next_sort_order += 1
            db.add(category)
            await db.flush()
            cat_by_name[key] = category
            categories_created += 1

        item = MenuItem(
            category_id=category.id,
            name=name,
            name_he=raw.get("nameHe"),
            description=raw.get("description"),
            price=float(raw.get("price") or 0),
        )
        db.add(item)
        await db.flush()
        items_created += 1

        printer_types = raw.get("printerTypes") or ([raw["printerType"]] if raw.get("printerType") else [])
        for printer_type in printer_types:
            printer = printer_by_type.get(printer_type)
            if not printer:
                unrouted.append(f"{name} ({printer_type})")
                continue
            existing_route = await db.execute(
                select(PrinterRoute).where(PrinterRoute.printer_id == printer.id, PrinterRoute.item_id == item.id)
            )
            if not existing_route.scalar_one_or_none():
                db.add(PrinterRoute(printer_id=printer.id, item_id=item.id))
                routes_created += 1

    await db.flush()
    del _menu_import_sessions[body.session_id]

    return {
        "categoriesCreated": categories_created,
        "itemsCreated": items_created,
        "routesCreated": routes_created,
        "unrouted": unrouted,
    }

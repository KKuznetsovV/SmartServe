"""AI command endpoint — intent classification, action preview, and menu import."""

import asyncio
import base64
import json
import uuid

import anthropic
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

router = APIRouter()
bearer = HTTPBearer()

# All supported intents — sent as context to Haiku for classification
SUPPORTED_INTENTS = [
    "menu.create_item",
    "menu.update_item",
    "menu.bulk_price_change",
    "menu.toggle_availability",
    "menu.create_category",
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
- "Send pasta orders to the kitchen printer" → intent: printer.route, params: {{category_hint: "pasta", printer_hint: "kitchen"}}
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


@router.post("/confirm")
async def ai_confirm(
    body: ConfirmRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    decode_token(credentials.credentials)

    pending = _pending.pop(body.execution_id, None)
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found or already confirmed")

    # TODO: dispatch to the appropriate service based on intent (implemented in step/08)
    return {"success": True, "message": f"Action '{pending['intent']}' queued for execution"}


# ─── Menu import (upload a menu photo/PDF/sheet, AI extracts + organizes it) ──

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
SUPPORTED_TEXT_TYPES = {"text/plain", "text/csv"}
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB

MENU_IMPORT_SYSTEM_PROMPT = """You are a menu-import assistant for SmartServe, a restaurant POS system.
You are shown a photo, screenshot, PDF, or text/spreadsheet export of a restaurant's menu (English or Hebrew).

Extract every distinct menu item you can find: name, an optional short description, and its price.
For each item, suggest:
- "category": a short category name (use one of the business's EXISTING categories below when it clearly fits,
  otherwise propose a new, sensible category name)
- "printerType": one of "kitchen", "receipt", "label", or null if you are not confident — pick based on the
  business's EXISTING printers below (e.g. food categories usually route to a "kitchen" printer, drinks/receipts
  to a "receipt" printer)

This business's existing categories: {categories}
This business's existing printers (name/type): {printers}

Return ONLY valid JSON, no markdown fences, in exactly this format:
{{
  "items": [
    {{"name": "...", "nameHe": null, "description": null, "price": 42.0, "currency": "ILS",
      "category": "...", "printerType": "kitchen"}}
  ],
  "message": "<a short reply to the user, in the language they used>",
  "needsClarification": <true|false>
}}

Set "needsClarification" to true and use "message" to ask a specific, single follow-up question when: prices are
missing or illegible, a group of items has no obvious category, or printer routing for a category is genuinely
ambiguous between two existing printers of the same type. Otherwise set it to false and put a brief summary
(e.g. item count and categories found) in "message". Keep conversing with the user turn-by-turn until every item
has a clear category and, where possible, a printer assignment — incorporate their replies to refine "items".
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
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Please upload an image (PNG/JPEG/WEBP), a PDF, or a text/CSV file.",
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
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    result = _parse_json_reply(message)

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
        max_tokens=4096,
        system=system,
        messages=history,
    )
    result = _parse_json_reply(message)

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
        items_created += 1

        printer_type = raw.get("printerType")
        if printer_type:
            printer = printer_by_type.get(printer_type)
            if printer:
                existing_route = await db.execute(
                    select(PrinterRoute).where(
                        PrinterRoute.printer_id == printer.id, PrinterRoute.category_id == category.id
                    )
                )
                if not existing_route.scalar_one_or_none():
                    db.add(PrinterRoute(printer_id=printer.id, category_id=category.id))
                    routes_created += 1
            else:
                unrouted.append(name)

    await db.flush()
    del _menu_import_sessions[body.session_id]

    return {
        "categoriesCreated": categories_created,
        "itemsCreated": items_created,
        "routesCreated": routes_created,
        "unrouted": unrouted,
    }

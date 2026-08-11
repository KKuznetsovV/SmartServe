"""AI command endpoint — intent classification, action preview, and menu import."""

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
from app.modules.ai.schemas import CommandRequest, ConfirmRequest, MenuImportApplyRequest, MenuImportMessageRequest
from app.modules.ai.services.client import create_message, parse_json_reply, parse_menu_import_reply
from app.modules.ai.services.dispatch import dispatch_intent
from app.modules.ai.services.import_parsing import MAX_UPLOAD_SIZE, build_content_block, fetch_menu_context
from app.modules.ai.services.prompts import INTENT_SYSTEM_PROMPT, MENU_IMPORT_SYSTEM_PROMPT, SUPPORTED_INTENTS

router = APIRouter()
bearer = HTTPBearer()

# In-memory pending executions / import sessions (replace with Redis in step/02)
_pending: dict[str, dict] = {}
_menu_import_sessions: dict[str, dict] = {}


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

    message = await create_message(
        client,
        model=settings.AI_INTENT_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": body.message}],
    )

    try:
        result = parse_json_reply(message)
    except json.JSONDecodeError, IndexError, KeyError:
        # Fallback to Sonnet when Haiku produces malformed output
        message = await create_message(
            client,
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = parse_json_reply(message)

    confidence: float = result.get("confidence", 0)

    # If confidence is low, use Sonnet for a more careful classification
    if confidence < settings.AI_INTENT_CONFIDENCE_THRESHOLD:
        message = await create_message(
            client,
            model=settings.AI_COMPLEX_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": body.message}],
        )
        result = parse_json_reply(message)

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

    message = await dispatch_intent(intent, params, location_id, db)

    return {"success": True, "message": message}


async def _get_owned_location(db: AsyncSession, location_id: str, user: User) -> Location:
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location or location.business_id != user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


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

    block = build_content_block(content, file.content_type or "", file.filename or "upload")
    categories, printers = await fetch_menu_context(db, location.id)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_IMPORT_SYSTEM_PROMPT.format(categories=categories, printers=printers)
    user_content = [block, {"type": "text", "text": "Extract the menu items from this file."}]

    message = await create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    result = parse_menu_import_reply(message)

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

    categories, printers = await fetch_menu_context(db, session["location_id"])
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system = MENU_IMPORT_SYSTEM_PROMPT.format(categories=categories, printers=printers)

    history = [*session["history"], {"role": "user", "content": body.message}]

    message = await create_message(
        client,
        model=settings.AI_COMPLEX_MODEL,
        max_tokens=8192,
        system=system,
        messages=history,
    )
    result = parse_menu_import_reply(message)

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

"""AI command endpoint — intent classification, action preview, and menu import."""

import json
import uuid
from datetime import UTC, datetime

import anthropic
from fastapi import Depends, File, Form, HTTPException, Request, UploadFile, status
from httpx import HTTPStatusError

from app.api.v1.deps import AuthContext, get_auth_context, require_manager
from app.api.v1.router_base import APIRouter
from app.clients import auth_client
from app.core import mq
from app.core.config import settings
from app.modules.ai.schemas import CommandRequest, ConfirmRequest, MenuImportApplyRequest, MenuImportMessageRequest
from app.modules.ai.services.client import create_message, parse_json_reply, parse_menu_import_reply
from app.modules.ai.services.dispatch import dispatch_intent
from app.modules.ai.services.import_parsing import MAX_UPLOAD_SIZE, build_content_block, fetch_menu_context
from app.modules.ai.services.menu_client import MenuClient, PrintingClient
from app.modules.ai.services.prompts import INTENT_SYSTEM_PROMPT, MENU_IMPORT_SYSTEM_PROMPT, SUPPORTED_INTENTS
from app.modules.ai.services.report_dispatch import generate_report

router = APIRouter()

_PENDING_TTL = 600  # 10 minutes
_IMPORT_TTL = 1800  # 30 minutes


@router.post("/command")
async def ai_command(
    body: CommandRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),  # validates the JWT; any authenticated role may ask
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    # location_id/business_id are never trusted bare from the body — the location is
    # confirmed to belong to the caller's own (JWT-verified) business here, same check
    # `ai_confirm` already does, so a classify call can't be used to probe/target another
    # business's location before a confirm is ever attempted.
    location_id = body.context.get("locationId") if isinstance(body.context, dict) else None
    if not location_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing location context")
    await _get_owned_location(location_id, ctx)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system = INTENT_SYSTEM_PROMPT.format(
        intents=", ".join(SUPPORTED_INTENTS), today=datetime.now(UTC).date().isoformat()
    )

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

    intent = result.get("intent")
    params = result.get("params", {})

    # report.query is read-only and never mutates data, so it skips the pending-execution/
    # /confirm flow entirely and answers immediately — but reports are still sensitive
    # business data, so it's gated to managers/owners just like reporting's own endpoints.
    if intent == "report.query":
        if ctx.claims.role not in ("owner", "manager"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers can run reports")
        report = await generate_report(params, location_id, ctx.token)
        return {
            "intent": intent,
            "confidence": result.get("confidence"),
            "params": params,
            "preview": result.get("preview", ""),
            "requiresConfirmation": False,
            "report": report,
        }

    execution_id = str(uuid.uuid4())
    await request.app.state.redis.setex(
        f"ai:pending:{execution_id}",
        _PENDING_TTL,
        json.dumps({"intent": intent, "params": params, "context": body.context, "message": body.message}),
    )

    return {
        "intent": intent,
        "confidence": result.get("confidence"),
        "params": params,
        "preview": result.get("preview", ""),
        "requiresConfirmation": True,
        "executionId": execution_id,
    }


@router.post("/confirm")
async def ai_confirm(
    body: ConfirmRequest,
    request: Request,
    ctx: AuthContext = Depends(require_manager),
):
    raw = await request.app.state.redis.getdel(f"ai:pending:{body.execution_id}")
    pending = json.loads(raw) if raw else None
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found or already confirmed")

    intent = pending["intent"]
    params = pending.get("params") or {}
    context = pending.get("context") or {}

    location_id = context.get("locationId")
    if not location_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing location context")
    await _get_owned_location(location_id, ctx)

    menu = MenuClient(ctx.token)
    printing = PrintingClient(ctx.token)
    original_message = pending.get("message", "")
    message = await dispatch_intent(intent, params, location_id, menu, printing)

    # Audit log: who ran the assistant, what it was asked, and what it actually did —
    # consumed by `reporting`'s wildcard EventLog subscriber (GET /reports/events).
    await mq.publish(
        request.app.state.mq_connection,
        "ai.action_executed",
        {
            "intent": intent,
            "params": params,
            "locationId": location_id,
            "businessId": ctx.claims.business_id,
            "userId": ctx.claims.sub,
            "originalMessage": original_message,
            "message": message,
        },
    )

    return {"success": True, "message": message}


async def _get_owned_location(location_id: str, ctx: AuthContext) -> dict:
    try:
        resp = await auth_client.get(f"/api/v1/locations/{location_id}", forward_token=ctx.token)
    except HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="auth service error") from exc

    location = resp.json()
    if location.get("businessId") != ctx.claims.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@router.post("/menu-import")
async def menu_import_start(
    request: Request,
    location_id: str = Form(...),
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(require_manager),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    location = await _get_owned_location(location_id, ctx)

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 15MB)")

    block = build_content_block(content, file.content_type or "", file.filename or "upload")
    menu = MenuClient(ctx.token)
    printing = PrintingClient(ctx.token)
    categories, printers = await fetch_menu_context(menu, printing, location["id"])

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
    await request.app.state.redis.setex(
        f"ai:import:{session_id}",
        _IMPORT_TTL,
        json.dumps({
            "business_id": ctx.claims.business_id,
            "location_id": location["id"],
            "items": result.get("items", []),
            "history": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": json.dumps(result)},
            ],
        }),
    )

    return {
        "sessionId": session_id,
        "items": result.get("items", []),
        "message": result.get("message", ""),
        "needsClarification": result.get("needsClarification", False),
    }


@router.post("/menu-import/message")
async def menu_import_message(
    body: MenuImportMessageRequest,
    request: Request,
    ctx: AuthContext = Depends(require_manager),
):
    raw = await request.app.state.redis.get(f"ai:import:{body.session_id}")
    session = json.loads(raw) if raw else None
    if not session or session["business_id"] != ctx.claims.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session not found")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured (set ANTHROPIC_API_KEY)",
        )

    menu = MenuClient(ctx.token)
    printing = PrintingClient(ctx.token)
    categories, printers = await fetch_menu_context(menu, printing, session["location_id"])
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
    await request.app.state.redis.setex(f"ai:import:{body.session_id}", _IMPORT_TTL, json.dumps(session))

    return {
        "sessionId": body.session_id,
        "items": session["items"],
        "message": result.get("message", ""),
        "needsClarification": result.get("needsClarification", False),
    }


@router.post("/menu-import/apply")
async def menu_import_apply(
    body: MenuImportApplyRequest,
    request: Request,
    ctx: AuthContext = Depends(require_manager),
):
    raw = await request.app.state.redis.get(f"ai:import:{body.session_id}")
    session = json.loads(raw) if raw else None
    if not session or session["business_id"] != ctx.claims.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session not found")

    location_id = session["location_id"]
    items = body.items if body.items is not None else session["items"]

    menu = MenuClient(ctx.token)
    printing = PrintingClient(ctx.token)

    existing_cats = await menu.list_categories(location_id)
    cat_by_name = {c["name"].strip().lower(): c for c in existing_cats}
    existing_printers = await printing.list_printers(location_id)
    printer_by_type: dict[str, dict] = {}
    for p in existing_printers:
        printer_by_type.setdefault(p["type"], p)

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
            category = await menu.create_category(
                location_id=location_id, name=category_name, sort_order=next_sort_order
            )
            next_sort_order += 1
            cat_by_name[key] = category
            categories_created += 1

        item = await menu.create_item(
            category_id=category["id"],
            name=name,
            name_he=raw.get("nameHe"),
            description=raw.get("description"),
            price=float(raw.get("price") or 0),
        )
        items_created += 1

        printer_types = raw.get("printerTypes") or ([raw["printerType"]] if raw.get("printerType") else [])
        for printer_type in printer_types:
            printer = printer_by_type.get(printer_type)
            if not printer:
                unrouted.append(f"{name} ({printer_type})")
                continue
            # add_route is idempotent, so routes_created counts attempted routings for a fresh
            # import (not strictly "newly created" like the old in-process count could tell)
            await printing.add_route(printer["id"], item["id"])
            routes_created += 1

    await request.app.state.redis.delete(f"ai:import:{body.session_id}")

    return {
        "categoriesCreated": categories_created,
        "itemsCreated": items_created,
        "routesCreated": routes_created,
        "unrouted": unrouted,
    }

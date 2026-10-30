"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4)."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PrinterRoute, PrintJob

logger = structlog.get_logger()


async def handle_order_item_fired(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    """`ordering` publishes this when a fired course releases items to the kitchen.

    No real physical printer driver exists yet — this fans the item out to every printer
    routed to it and records a `PrintJob` row per match, purely as an audit trail.
    Writes use the session from `handle_idempotent` and commit with the processed-event row.
    """
    order_id = payload.get("orderId")
    item_id = payload.get("itemId")
    menu_item_id = payload.get("menuItemId")
    if not order_id or not item_id or not menu_item_id:
        logger.warning("printing.events: order.item_fired missing required fields", payload=payload)
        return

    result = await db.execute(select(PrinterRoute).where(PrinterRoute.item_id == menu_item_id))
    routes = list(result.scalars().all())
    if not routes:
        return
    for route in routes:
        db.add(PrintJob(order_id=order_id, item_id=item_id, printer_id=route.printer_id))

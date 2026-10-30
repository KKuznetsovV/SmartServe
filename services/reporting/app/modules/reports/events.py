"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4).

Reporting binds a single queue to the wildcard routing key `#`, so every event published on
the `smartserve.events` exchange lands here — this is the general audit/event log for the
whole platform. Order events project into reporting-owned tables; they never write `orders`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLog, ReportingOrder, ReportingOrderItem

logger = structlog.get_logger()


def _business_id_from_payload(payload: dict[str, Any]) -> str | None:
    raw = payload.get("businessId")
    if isinstance(raw, str) and raw:
        return raw
    return None


def _event_version(payload: dict[str, Any]) -> int:
    raw = payload.get("version")
    if isinstance(raw, bool) or raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0


def _event_occurred_at(payload: dict[str, Any]) -> datetime:
    raw = payload.get("occurredAt")
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    created_at = payload.get("createdAt")
    if isinstance(created_at, str) and created_at:
        try:
            return datetime.fromisoformat(created_at)
        except ValueError:
            pass
    return datetime.now(UTC)


async def handle_any_event(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    db.add(
        EventLog(
            routing_key=routing_key,
            payload=json.dumps(payload),
            business_id=_business_id_from_payload(payload),
        )
    )

    if routing_key in ("order.created", "order.updated"):
        await _project_order(db, payload)
    elif routing_key == "payment.completed":
        await _mark_order_paid(db, payload)


async def _project_order(db, payload: dict[str, Any]) -> None:
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("reporting.events: order event missing orderId", payload=payload)
        return
    incoming_version = _event_version(payload)
    result = await db.execute(select(ReportingOrder).where(ReportingOrder.id == order_id))
    row = result.scalar_one_or_none()
    if row is not None and incoming_version <= row.version:
        return

    occurred_at = _event_occurred_at(payload)
    created_at = payload.get("createdAt")
    created_dt = datetime.fromisoformat(created_at) if isinstance(created_at, str) and created_at else occurred_at

    if row is None:
        row = ReportingOrder(
            id=order_id,
            location_id=payload.get("locationId", ""),
            channel=payload.get("channel", "dine_in"),
            status=payload.get("status", "open"),
            total=payload.get("total", 0.0),
            created_by=payload.get("createdBy"),
            created_at=created_dt,
            version=incoming_version,
            occurred_at=occurred_at,
        )
        db.add(row)
    else:
        if "locationId" in payload:
            row.location_id = payload["locationId"] or row.location_id
        if "channel" in payload:
            row.channel = payload["channel"] or row.channel
        if "status" in payload:
            row.status = payload["status"]
        if "total" in payload:
            row.total = payload["total"]
        if "createdBy" in payload:
            row.created_by = payload["createdBy"]
        row.version = incoming_version
        row.occurred_at = occurred_at

    if "items" in payload:
        await db.execute(delete(ReportingOrderItem).where(ReportingOrderItem.order_id == order_id))
        for item in payload.get("items") or []:
            item_id = item.get("id")
            name = item.get("menuItemName")
            if not item_id or not name:
                continue
            db.add(
                ReportingOrderItem(
                    id=item_id,
                    order_id=order_id,
                    menu_item_id=item.get("menuItemId"),
                    menu_item_name=name,
                    category_id=item.get("categoryId"),
                    category_name=item.get("categoryName"),
                    qty=int(item.get("qty") or 1),
                    unit_price=float(item.get("unitPrice") or 0.0),
                )
            )


async def _mark_order_paid(db, payload: dict[str, Any]) -> None:
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("reporting.events: payment.completed missing orderId", payload=payload)
        return
    result = await db.execute(select(ReportingOrder).where(ReportingOrder.id == order_id))
    row = result.scalar_one_or_none()
    if row is None:
        return
    incoming_version = _event_version(payload)
    if incoming_version and incoming_version <= row.version:
        return
    row.status = "paid"
    row.version = incoming_version or (row.version + 1)
    row.occurred_at = _event_occurred_at(payload)

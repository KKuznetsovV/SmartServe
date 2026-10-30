"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4).

Reporting binds a single queue to the wildcard routing key `#`, so every event published on
the `smartserve.events` exchange lands here — this is the general audit/event log for the
whole platform. A handful of routing keys are additionally used to keep reporting's own
Order mirror (used by the summary/analytics endpoints) up to date, since nothing else ever
populated it before this event bus existed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.db.models import EventLog, Order
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger()


def _business_id_from_payload(payload: dict[str, Any]) -> str | None:
    raw = payload.get("businessId")
    if isinstance(raw, str) and raw:
        return raw
    return None


async def handle_any_event(routing_key: str, payload: dict[str, Any]) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            EventLog(
                routing_key=routing_key,
                payload=json.dumps(payload),
                business_id=_business_id_from_payload(payload),
            )
        )

        if routing_key == "order.created":
            await _upsert_order(db, payload)
        elif routing_key == "order.updated":
            await _update_order_status(db, payload)
        elif routing_key == "payment.completed":
            await _mark_order_paid(db, payload)

        await db.commit()


async def _upsert_order(db, payload: dict[str, Any]) -> None:
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("reporting.events: order.created missing orderId", payload=payload)
        return
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    created_at = payload.get("createdAt")
    if order is None:
        order = Order(
            id=order_id,
            location_id=payload.get("locationId", ""),
            channel=payload.get("channel", "dine_in"),
            status=payload.get("status", "open"),
            total=payload.get("total", 0.0),
            created_by=payload.get("createdBy"),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(UTC),
        )
        db.add(order)
    else:
        order.location_id = payload.get("locationId", order.location_id)
        order.channel = payload.get("channel", order.channel)
        order.status = payload.get("status", order.status)
        order.total = payload.get("total", order.total)
        order.created_by = payload.get("createdBy", order.created_by)


async def _update_order_status(db, payload: dict[str, Any]) -> None:
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("reporting.events: order.updated missing orderId", payload=payload)
        return
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        return
    order.status = payload.get("status", order.status)
    order.total = payload.get("total", order.total)


async def _mark_order_paid(db, payload: dict[str, Any]) -> None:
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("reporting.events: payment.completed missing orderId", payload=payload)
        return
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        return
    order.status = "paid"

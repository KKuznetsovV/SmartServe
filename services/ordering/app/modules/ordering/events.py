"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderItem
from app.modules.ordering.ws_router import publish_ws

logger = structlog.get_logger()

_WS_FIELDS = ("orderId", "id", "itemId", "status", "orderNumber", "tableName", "locationId")


def order_event_payload(order: Order, business_id: str) -> dict[str, Any]:
    """Bump `orders.version` and build the projection payload for one order event."""
    order.version = int(order.version or 0) + 1
    occurred_at = datetime.now(UTC)
    items: list[dict[str, Any]] = []
    if "items" not in inspect(order).unloaded:
        for item in order.items:
            items.append(_item_snapshot(item))
    created_at = order.created_at.isoformat() if order.created_at else occurred_at.isoformat()
    return {
        "orderId": order.id,
        "locationId": order.location_id,
        "businessId": business_id,
        "channel": order.channel,
        "status": order.status,
        "total": order.total,
        "taxAmount": order.tax_amount,
        "createdBy": order.created_by,
        "createdAt": created_at,
        "version": order.version,
        "occurredAt": occurred_at.isoformat(),
        "tableName": order.table_name,
        "orderNumber": order.order_number,
        "items": items,
    }


def _item_snapshot(item: OrderItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "menuItemId": item.menu_item_id,
        "menuItemName": item.menu_item_name,
        "categoryId": item.category_id,
        "categoryName": item.category_name,
        "qty": item.qty,
        "unitPrice": item.unit_price,
    }


async def handle_payment_event(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    if routing_key == "payment.refunded":
        await handle_payment_refunded(routing_key, payload, db)
        return
    await handle_payment_completed(routing_key, payload, db)


async def handle_payment_completed(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    """`payments` publishes this once a payment covers an order's total.

    `ordering` owns the canonical `Order.status` (payments only holds a local mirror used
    for its own duplicate-payment checks), so this marks the real row paid here rather than
    relying on payments' write. Idempotent — a redelivered/duplicate event is a no-op.
    Writes use the session from `handle_idempotent` and commit with the processed-event row.
    """
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("ordering.events: payment.completed missing orderId", payload=payload)
        return
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        logger.warning("ordering.events: payment.completed for unknown order", order_id=order_id)
        return
    if order.status not in ("paid", "cancelled"):
        order.status = "paid"
        order.version = int(order.version or 0) + 1


async def handle_payment_refunded(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    """A refund re-opens a paid ticket so the floor can collect again."""
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("ordering.events: payment.refunded missing orderId", payload=payload)
        return
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        logger.warning("ordering.events: payment.refunded for unknown order", order_id=order_id)
        return
    if order.status == "paid":
        order.status = "served"
        order.version = int(order.version or 0) + 1


def ws_event_type(routing_key: str) -> str:
    if routing_key == "catalog.item_updated":
        return "menu.item_updated"
    return routing_key


def slim_ws_payload(routing_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Ids, status, orderNumber and tableName only — no totals, notes or staff ids."""
    if routing_key == "catalog.item_updated":
        return {key: payload[key] for key in ("itemId", "locationId") if payload.get(key)}
    body = {key: payload[key] for key in _WS_FIELDS if payload.get(key) not in (None, "")}
    if "orderId" in body and "id" not in body:
        body["id"] = body["orderId"]
    return body


async def handle_realtime(routing_key: str, payload: dict[str, Any], _db: AsyncSession) -> None:
    """Committed `order.*` and `catalog.item_updated` events fan out over Redis `ws:{locationId}`."""
    location_id = payload.get("locationId")
    if not isinstance(location_id, str) or not location_id:
        logger.warning("ordering.events: realtime event missing locationId", routing_key=routing_key)
        return
    await publish_ws(
        location_id,
        {
            "type": ws_event_type(routing_key),
            "locationId": location_id,
            "payload": slim_ws_payload(routing_key, payload),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def handle_catalog_item_updated(routing_key: str, payload: dict[str, Any], db: AsyncSession) -> None:
    await handle_realtime(routing_key, payload, db)

"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import inspect, select

from app.db.models import Order, OrderItem
from app.db.session import AsyncSessionLocal
from app.modules.ordering.ws_router import broadcast

logger = structlog.get_logger()


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
        "createdBy": order.created_by,
        "createdAt": created_at,
        "version": order.version,
        "occurredAt": occurred_at.isoformat(),
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


async def handle_payment_completed(routing_key: str, payload: dict[str, Any]) -> None:
    """`payments` publishes this once a payment covers an order's total.

    `ordering` owns the canonical `Order.status` (payments only holds a local mirror used
    for its own duplicate-payment checks), so this marks the real row paid here rather than
    relying on payments' write. Idempotent — a redelivered/duplicate event is a no-op.
    """
    order_id = payload.get("orderId")
    if not order_id:
        logger.warning("ordering.events: payment.completed missing orderId", payload=payload)
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            logger.warning("ordering.events: payment.completed for unknown order", order_id=order_id)
            return
        if order.status not in ("paid", "cancelled"):
            order.status = "paid"
            order.version = int(order.version or 0) + 1
            await db.commit()


async def handle_catalog_item_updated(routing_key: str, payload: dict[str, Any]) -> None:
    """`catalog` publishes this on every menu item create/update/stock/bulk-price change.

    `ordering` owns the only real-time websocket hub connected frontends already have a
    live connection to (`/api/v1/ws/{location_id}`, the sole path the gateway proxies for
    websockets — see docs/microservices-plan.md §5), so cross-domain updates are relayed
    here rather than every domain standing up its own websocket endpoint. This keeps "one
    websocket connection per location" true for frontends regardless of which service's
    data actually changed.
    """
    location_id = payload.get("locationId")
    if not location_id:
        logger.warning("ordering.events: catalog.item_updated missing locationId", payload=payload)
        return
    await broadcast(
        location_id,
        {
            "type": "menu.item_updated",
            "locationId": location_id,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

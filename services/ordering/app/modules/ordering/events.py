"""Consumer handlers for events published by other services (see docs/microservices-plan.md §4)."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from app.db.models import Order
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger()


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
            await db.commit()

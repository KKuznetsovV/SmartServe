from datetime import UTC, datetime

from fastapi import Depends, Query, Request
from smartserve_shared.outbox import enqueue
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_staff
from app.db.models import Outbox, User
from app.db.session import DbSession
from app.modules.ordering.events import order_event_payload
from app.modules.ordering.schemas import (
    ApplyDiscountIn,
    AssignGuestsRequest,
    OrderCreate,
    OrderFireCourseRequest,
    OrderItemCompRequest,
    OrderItemCreate,
    OrderItemDeleteRequest,
    OrderItemDiscountRequest,
    OrderItemOut,
    OrderItemStatusUpdate,
    OrderItemUpdate,
    OrderWithItemsOut,
    ReorderRequest,
)
from app.modules.ordering.service import OrderService

router = APIRouter()


async def _publish_order_event(db, order, business_id: str, routing_key: str) -> dict:
    payload = order_event_payload(order, business_id)
    await enqueue(db, Outbox, routing_key, payload, business_id=business_id)
    return payload


async def _enqueue_unfired_pending(db, order, business_id: str) -> None:
    """One `order.item_fired` per pending line, never twice (`fired_at` in the same TX)."""
    if order.status == "open":
        return
    now = datetime.now(UTC)
    for item in order.items:
        if item.status != "pending" or item.fired_at is not None:
            continue
        item.fired_at = now
        await enqueue(
            db,
            Outbox,
            "order.item_fired",
            {
                "orderId": order.id,
                "itemId": item.id,
                "menuItemId": item.menu_item_id,
                "menuItemName": item.menu_item_name,
                "locationId": order.location_id,
                "businessId": business_id,
                "course": item.fire_course,
            },
            business_id=business_id,
        )


@router.get("/locations/{location_id}/orders", response_model=list[OrderWithItemsOut])
async def list_orders(
    location_id: str,
    db: DbSession,
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).list_orders(
        location_id, status, limit=limit, offset=offset, business_id=current_user.business_id
    )


@router.get("/orders/{order_id}", response_model=OrderWithItemsOut)
async def get_order(
    order_id: str,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).get_order(order_id, current_user.business_id)


@router.post("/orders", response_model=OrderWithItemsOut, status_code=201)
async def create_order(
    data: OrderCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).create_order(data, created_by=current_user.id, business_id=current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.created")
    return order


@router.post("/orders/{order_id}/items", response_model=OrderItemOut, status_code=201)
async def add_order_item(
    order_id: str,
    data: OrderItemCreate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    item = await OrderService(db).add_item(order_id, data, current_user.business_id)
    order = await OrderService(db).get_order(order_id, current_user.business_id)
    await _enqueue_unfired_pending(db, order, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return item


@router.patch("/orders/{order_id}/items/{item_id}/status", response_model=OrderItemOut)
async def update_item_status(
    order_id: str,
    item_id: str,
    data: OrderItemStatusUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    item = await OrderService(db).update_item_status(order_id, item_id, data, current_user.business_id)
    order = await OrderService(db).get_order(order_id, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return item


@router.patch("/orders/{order_id}/items/{item_id}", response_model=OrderItemOut)
async def update_order_item(
    order_id: str,
    item_id: str,
    data: OrderItemUpdate,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    item = await OrderService(db).update_item(order_id, item_id, data, current_user.business_id)
    order = await OrderService(db).get_order(order_id, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return item


@router.post("/orders/{order_id}/items/reorder", status_code=204)
async def reorder_order_items(
    order_id: str,
    body: ReorderRequest,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    await OrderService(db).reorder_items(order_id, body.ids, current_user.business_id)


@router.delete("/orders/{order_id}/items/{item_id}", status_code=204)
async def remove_order_item(
    order_id: str,
    item_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    await OrderService(db).remove_item(order_id, item_id, current_user.business_id)
    order = await OrderService(db).get_order(order_id, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")


@router.post("/orders/{order_id}/submit", response_model=OrderWithItemsOut)
async def submit_order(
    order_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).transition_order(order_id, "submitted", current_user.business_id)
    await _enqueue_unfired_pending(db, order, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/cancel", response_model=OrderWithItemsOut)
async def cancel_order(
    order_id: str,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).transition_order(order_id, "cancelled", current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/discount", response_model=OrderWithItemsOut)
async def apply_discount(
    order_id: str,
    data: ApplyDiscountIn,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).apply_discount(order_id, data, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/items/assign-guests", response_model=OrderWithItemsOut)
async def assign_guests(
    order_id: str,
    data: AssignGuestsRequest,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).assign_guests(order_id, data, current_user.business_id)


@router.post("/orders/{order_id}/items/discount", response_model=OrderWithItemsOut)
async def apply_item_discount(
    order_id: str,
    data: OrderItemDiscountRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).apply_item_discount(order_id, data, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/items/comp", response_model=OrderWithItemsOut)
async def comp_items(
    order_id: str,
    data: OrderItemCompRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).set_item_comp(order_id, data, current_user.id, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/items/delete", response_model=OrderWithItemsOut)
async def bulk_delete_items(
    order_id: str,
    data: OrderItemDeleteRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).delete_items(order_id, data, current_user.business_id)
    await _publish_order_event(db, order, current_user.business_id, "order.updated")
    return order


@router.post("/orders/{order_id}/fire-course", response_model=OrderWithItemsOut)
async def fire_course(
    order_id: str,
    data: OrderFireCourseRequest,
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    result = await OrderService(db).fire_course(order_id, data, current_user.business_id)
    await _enqueue_unfired_pending(db, result, current_user.business_id)
    await _publish_order_event(db, result, current_user.business_id, "order.updated")
    return result


@router.get("/public/locations/{location_id}/orders", response_model=list[OrderWithItemsOut])
async def public_active_orders(
    location_id: str,
    db: DbSession,
):
    """No-auth endpoint for customer-facing display screens."""
    return await OrderService(db).list_active_for_display(location_id)

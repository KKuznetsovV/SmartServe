from fastapi import Depends, Query, Request
from smartserve_shared import mq
from smartserve_shared.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.db.models import User
from app.db.session import get_db
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
)
from app.modules.ordering.service import OrderService
from app.modules.ordering.ws_router import broadcast_event

router = APIRouter()


@router.get("/locations/{location_id}/orders", response_model=list[OrderWithItemsOut])
async def list_orders(
    location_id: str,
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).list_orders(
        location_id, status, limit=limit, offset=offset, business_id=current_user.business_id
    )


@router.get("/orders/{order_id}", response_model=OrderWithItemsOut)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).get_order(order_id, current_user.business_id)


@router.post("/orders", response_model=OrderWithItemsOut, status_code=201)
async def create_order(
    data: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).create_order(data, created_by=current_user.id, business_id=current_user.business_id)
    await mq.publish(
        request.app.state.mq_connection,
        "order.created",
        {
            "orderId": order.id,
            "locationId": order.location_id,
            "channel": order.channel,
            "status": order.status,
            "total": order.total,
            "createdBy": order.created_by,
            "createdAt": order.created_at.isoformat(),
        },
    )
    return order


@router.post("/orders/{order_id}/items", response_model=OrderItemOut, status_code=201)
async def add_order_item(
    order_id: str,
    data: OrderItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).add_item(order_id, data, current_user.business_id)


@router.patch("/orders/{order_id}/items/{item_id}/status", response_model=OrderItemOut)
async def update_item_status(
    order_id: str,
    item_id: str,
    data: OrderItemStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    item = await OrderService(db).update_item_status(order_id, item_id, data, current_user.business_id)
    order = await OrderService(db).get_order(order_id, current_user.business_id)
    await broadcast_event(
        order.location_id,
        "order.item_status_changed",
        {
            "orderId": order.id,
            "itemId": item.id,
            "status": item.status,
            "orderStatus": order.status,
            "locationId": order.location_id,
        },
    )
    return item


@router.patch("/orders/{order_id}/items/{item_id}", response_model=OrderItemOut)
async def update_order_item(
    order_id: str,
    item_id: str,
    data: OrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).update_item(order_id, item_id, data, current_user.business_id)


@router.post("/orders/{order_id}/items/reorder", status_code=204)
async def reorder_order_items(
    order_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    await OrderService(db).reorder_items(order_id, body["ids"], current_user.business_id)


@router.delete("/orders/{order_id}/items/{item_id}", status_code=204)
async def remove_order_item(
    order_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    await OrderService(db).remove_item(order_id, item_id, current_user.business_id)


@router.post("/orders/{order_id}/submit", response_model=OrderWithItemsOut)
async def submit_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).transition_order(order_id, "submitted", current_user.business_id)
    payload = {"orderId": order.id, "locationId": order.location_id, "status": order.status, "total": order.total}
    await mq.publish(request.app.state.mq_connection, "order.updated", payload)
    await broadcast_event(order.location_id, "order.updated", payload)
    return order


@router.post("/orders/{order_id}/cancel", response_model=OrderWithItemsOut)
async def cancel_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    order = await OrderService(db).transition_order(order_id, "cancelled", current_user.business_id)
    payload = {"orderId": order.id, "locationId": order.location_id, "status": order.status, "total": order.total}
    await mq.publish(request.app.state.mq_connection, "order.updated", payload)
    await broadcast_event(order.location_id, "order.updated", payload)
    return order


@router.post("/orders/{order_id}/discount", response_model=OrderWithItemsOut)
async def apply_discount(
    order_id: str,
    data: ApplyDiscountIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).apply_discount(order_id, data, current_user.business_id)


@router.post("/orders/{order_id}/items/assign-guests", response_model=OrderWithItemsOut)
async def assign_guests(
    order_id: str,
    data: AssignGuestsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).assign_guests(order_id, data, current_user.business_id)


@router.post("/orders/{order_id}/items/discount", response_model=OrderWithItemsOut)
async def apply_item_discount(
    order_id: str,
    data: OrderItemDiscountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).apply_item_discount(order_id, data, current_user.business_id)


@router.post("/orders/{order_id}/items/comp", response_model=OrderWithItemsOut)
async def comp_items(
    order_id: str,
    data: OrderItemCompRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).set_item_comp(order_id, data, current_user.id, current_user.business_id)


@router.post("/orders/{order_id}/items/delete", response_model=OrderWithItemsOut)
async def bulk_delete_items(
    order_id: str,
    data: OrderItemDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return await OrderService(db).delete_items(order_id, data, current_user.business_id)


@router.post("/orders/{order_id}/fire-course", response_model=OrderWithItemsOut)
async def fire_course(
    order_id: str,
    data: OrderFireCourseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    service = OrderService(db)
    order_before = await service.get_order(order_id, current_user.business_id)
    newly_fired = [i for i in order_before.items if i.status == "held" and i.fire_course == data.course]
    result = await service.fire_course(order_id, data, current_user.business_id)
    for item in newly_fired:
        await mq.publish(
            request.app.state.mq_connection,
            "order.item_fired",
            {
                "orderId": order_id,
                "itemId": item.id,
                "menuItemId": item.menu_item_id,
                "menuItemName": item.menu_item_name,
                "locationId": result.location_id,
                "course": data.course,
            },
        )
    await broadcast_event(
        result.location_id,
        "order.updated",
        {"orderId": result.id, "locationId": result.location_id, "status": result.status, "total": result.total},
    )
    return result


@router.get("/public/locations/{location_id}/orders", response_model=list[OrderWithItemsOut])
async def public_active_orders(
    location_id: str,
    db: AsyncSession = Depends(get_db),
):
    """No-auth endpoint for customer-facing display screens."""
    return await OrderService(db).list_active_for_display(location_id)

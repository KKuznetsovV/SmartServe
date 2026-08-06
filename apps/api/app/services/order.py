"""Order service — lifecycle management for orders and items."""

from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import MenuItem, Order, OrderItem, Table
from app.schemas.order import (
    OrderCreate,
    OrderFireCourseRequest,
    OrderItemCreate,
    OrderItemStatusUpdate,
    OrderItemUpdate,
    OrderSplitRequest,
)

VALID_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "open": {"submitted", "cancelled"},
    "submitted": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served"},
    "served": {"paid"},
    "paid": set(),
    "cancelled": set(),
    "split": set(),
}

VALID_ITEM_TRANSITIONS: dict[str, set[str]] = {
    # "ready" is reachable directly from "pending" too, since the kitchen display's
    # "All Ready" bulk action marks every active item ready in one step.
    "held": {"pending", "cancelled"},
    "pending": {"preparing", "ready", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served"},
    "served": set(),
    "cancelled": set(),
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_orders(
        self, location_id: str, status_filter: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Order]:
        q = select(Order).where(Order.location_id == location_id).options(selectinload(Order.items))
        if status_filter:
            q = q.where(Order.status == status_filter)
        q = q.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def list_active_for_display(self, location_id: str) -> list[Order]:
        """Returns submitted/preparing/ready orders sorted oldest-first for display screens."""
        q = (
            select(Order)
            .where(Order.location_id == location_id, Order.status.in_(["submitted", "preparing", "ready"]))
            .options(selectinload(Order.items))
            .order_by(Order.created_at.asc())
            .limit(50)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_order(self, order_id: str) -> Order:
        result = await self.db.execute(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def create_order(self, data: OrderCreate) -> Order:
        if data.table_id:
            table_result = await self.db.execute(select(Table).where(Table.id == data.table_id, Table.active))
            if not table_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

        if data.channel == "dine_in" and (data.guest_count is None or data.guest_count < 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of guests is required for dine-in orders",
            )

        order = Order(
            location_id=data.location_id,
            table_id=data.table_id,
            channel=data.channel,
            guest_count=data.guest_count,
            notes=data.notes,
            status="open",
            subtotal=0.0,
            tax_amount=0.0,
            total=0.0,
        )
        self.db.add(order)
        await self.db.flush()
        return await self.get_order(order.id)

    async def add_item(self, order_id: str, data: OrderItemCreate) -> OrderItem:
        order = await self.get_order(order_id)
        if order.status not in ("open", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add items to an order that is already being prepared",
            )

        item_result = await self.db.execute(select(MenuItem).where(MenuItem.id == data.menu_item_id, MenuItem.active))
        menu_item = item_result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found or unavailable")
        if not menu_item.in_stock:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Menu item is out of stock")

        modifier_total = sum(m.price_delta for m in data.modifiers)
        unit_price = menu_item.price + modifier_total
        fire_course = data.fire_course if data.fire_course is not None else menu_item.default_fire_course

        order_item = OrderItem(
            order_id=order_id,
            menu_item_id=data.menu_item_id,
            menu_item_name=menu_item.name,
            qty=data.qty,
            unit_price=unit_price,
            modifiers=[m.model_dump() for m in data.modifiers],
            notes=data.notes,
            status="held" if fire_course > 1 else "pending",
            sort_order=len(order.items),
            fire_course=fire_course,
        )
        self.db.add(order_item)

        # Recalculate order totals
        await self._recalculate_totals(order, menu_item.tax_rate, unit_price * data.qty)
        await self.db.flush()
        return order_item

    async def update_item(self, order_id: str, item_id: str, data: OrderItemUpdate) -> OrderItem:
        """Adjust quantity, notes, or modifiers/customization of an item already on the order."""
        order = await self.get_order(order_id)
        if order.status not in ("open", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit items on an order that is already being prepared",
            )
        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
        if item.status in ("served", "cancelled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot edit a '{item.status}' item")

        menu_item_result = await self.db.execute(select(MenuItem).where(MenuItem.id == item.menu_item_id))
        menu_item = menu_item_result.scalar_one_or_none()
        tax_rate = menu_item.tax_rate if menu_item else 0.0
        base_price = menu_item.price if menu_item else item.unit_price - sum(m["price_delta"] for m in item.modifiers)

        old_total = item.unit_price * item.qty

        if data.modifiers is not None:
            item.modifiers = [m.model_dump() for m in data.modifiers]
            item.unit_price = base_price + sum(m.price_delta for m in data.modifiers)
        if data.qty is not None:
            item.qty = data.qty
        if data.notes is not None:
            item.notes = data.notes or None
        if data.fire_course is not None:
            if item.status == "held" and data.fire_course == 1:
                item.status = "pending"
            elif item.status == "pending" and data.fire_course > 1:
                item.status = "held"
            item.fire_course = data.fire_course

        new_total = item.unit_price * item.qty
        await self._recalculate_totals(order, tax_rate, new_total - old_total)
        await self.db.flush()
        return item

    async def update_item_status(self, order_id: str, item_id: str, data: OrderItemStatusUpdate) -> OrderItem:
        result = await self.db.execute(select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

        if data.status not in VALID_ITEM_TRANSITIONS.get(item.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition item from '{item.status}' to '{data.status}'",
            )

        item.status = data.status
        await self.db.flush()
        return item

    async def reorder_items(self, order_id: str, ids: list[str]) -> None:
        for order, item_id in enumerate(ids):
            await self.db.execute(
                update(OrderItem)
                .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
                .values(sort_order=order)
            )

    async def remove_item(self, order_id: str, item_id: str) -> None:
        order = await self.get_order(order_id)
        if order.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove items once the order has been submitted; cancel the item instead",
            )
        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

        menu_item_result = await self.db.execute(select(MenuItem).where(MenuItem.id == item.menu_item_id))
        menu_item = menu_item_result.scalar_one_or_none()
        tax_rate = menu_item.tax_rate if menu_item else 0.0
        item_total = -(item.unit_price * item.qty)

        # Remove from the already-loaded in-memory collection too — deleting the
        # row alone doesn't sync the parent's cached `items` list within the same
        # session, which would otherwise still show the deleted item on refetch.
        order.items.remove(item)
        await self.db.delete(item)
        await self.db.flush()
        await self._recalculate_totals(order, tax_rate, item_total)

    async def transition_order(self, order_id: str, new_status: str) -> Order:
        order = await self.get_order(order_id)
        if new_status not in VALID_ORDER_TRANSITIONS.get(order.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition order from '{order.status}' to '{new_status}'",
            )
        order.status = new_status
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return order

    async def fire_course(self, order_id: str, data: OrderFireCourseRequest) -> Order:
        """Release all 'held' items of the given fire course so the kitchen can start them."""
        order = await self.get_order(order_id)
        if order.status not in ("submitted", "preparing", "ready"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only fire a course on an order that has been submitted to the kitchen",
            )
        held_items = [i for i in order.items if i.status == "held" and i.fire_course == data.course]
        if not held_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No held items found for course {data.course}",
            )

        for item in held_items:
            item.status = "pending"

        if data.course not in order.fired_courses:
            order.fired_courses = [*order.fired_courses, data.course]
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self.get_order(order_id)

    async def split_order(self, order_id: str, data: OrderSplitRequest) -> list[Order]:
        """Split an open order into separate child orders, one per guest number.

        Every item on the order must be assigned to a guest; each resulting child
        order is a normal standalone order (own kitchen ticket, own payment) linked
        back to the original via split_from_order_id.
        """
        order = await self.get_order(order_id)
        if order.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only open orders can be split",
            )
        if not order.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order has no items to split")

        item_map = {item.id: item for item in order.items}
        assigned_ids = {a.item_id for a in data.assignments}
        if assigned_ids != set(item_map.keys()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every item on the order must be assigned to a guest to split it",
            )

        by_guest: dict[int, list[OrderItem]] = defaultdict(list)
        for assignment in data.assignments:
            by_guest[assignment.guest_number].append(item_map[assignment.item_id])

        if len(by_guest) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Split requires items to be assigned to at least two different guests",
            )

        children: list[Order] = []
        for guest_number, items in by_guest.items():
            child = Order(
                location_id=order.location_id,
                table_id=order.table_id,
                channel=order.channel,
                guest_count=order.guest_count,
                guest_number=guest_number,
                split_from_order_id=order.id,
                status="open",
                subtotal=0.0,
                tax_amount=0.0,
                total=0.0,
            )
            self.db.add(child)
            await self.db.flush()

            for item in items:
                item.order_id = child.id

            menu_item_result = await self.db.execute(select(MenuItem).where(MenuItem.id == items[0].menu_item_id))
            menu_item = menu_item_result.scalar_one_or_none()
            tax_rate = menu_item.tax_rate if menu_item else 0.0
            child.subtotal = round(sum(i.unit_price * i.qty for i in items), 2)
            child.tax_amount = round(child.subtotal * tax_rate, 2)
            child.total = round(child.subtotal + child.tax_amount, 2)
            children.append(child)

        order.status = "split"
        order.subtotal = 0.0
        order.tax_amount = 0.0
        order.total = 0.0
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return [await self.get_order(child.id) for child in children]

    async def _recalculate_totals(self, order: Order, tax_rate: float, item_total: float) -> None:
        order.subtotal = round(order.subtotal + item_total, 2)
        order.tax_amount = round(order.subtotal * tax_rate, 2)
        order.total = round(order.subtotal + order.tax_amount, 2)

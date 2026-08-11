"""Order service — lifecycle management for orders and items."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.db.models import Location, MenuItem, Order, OrderItem, Table, User
from app.modules.ordering.schemas import (
    AssignGuestsRequest,
    OrderCreate,
    OrderFireCourseRequest,
    OrderItemCompRequest,
    OrderItemCreate,
    OrderItemDeleteRequest,
    OrderItemDiscountRequest,
    OrderItemStatusUpdate,
    OrderItemUpdate,
)

VALID_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "open": {"submitted", "cancelled"},
    "submitted": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served"},
    "served": {"paid"},
    "paid": set(),
    "cancelled": set(),
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

    async def _verify_manager_pin(self, location_id: str, manager_user_id: str, pin: str) -> User:
        """Confirm a manager/owner override PIN without issuing a session token.

        `auth` (services/auth) owns the `users`/`locations` tables and is the source of truth
        for login/PIN issuance, but this is a same-database, read-only check — no need for a
        network round trip to `auth` for every override (see docs/microservices-plan.md §4).
        """
        loc_result = await self.db.execute(select(Location).where(Location.id == location_id, Location.active))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager PIN")

        result = await self.db.execute(
            select(User).where(
                User.id == manager_user_id,
                User.business_id == location.business_id,
                User.role.in_(["owner", "manager"]),
                User.active,
                User.pin_hash.is_not(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not user.pin_hash or not verify_password(pin, user.pin_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager PIN")
        return user

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

    async def assign_guests(self, order_id: str, data: AssignGuestsRequest) -> Order:
        """Optionally tag items with a guest number so a table's single order/check can
        still be organized or paid per-guest — this never creates a separate Order."""
        order = await self.get_order(order_id)
        if order.status in ("paid", "cancelled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a closed order")

        item_map = {item.id: item for item in order.items}
        for assignment in data.assignments:
            item = item_map.get(assignment.item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
            item = await self._split_item_for_quantity(order, item, assignment.quantity)
            item.guest_number = assignment.guest_number

        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self.get_order(order_id)

    async def apply_item_discount(self, order_id: str, data: OrderItemDiscountRequest) -> Order:
        """Apply (or clear, when both fields are None) a manual %/fixed discount to one or
        more items on the order — distinct from the order-level discount-code feature."""
        order = await self.get_order(order_id)
        if order.status in ("paid", "cancelled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a closed order")
        if data.discount_type is not None and data.discount_type not in ("percent", "fixed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="discount_type must be 'percent' or 'fixed'"
            )

        item_map = {item.id: item for item in order.items}
        for selection in data.items:
            item = item_map.get(selection.item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
            item = await self._split_item_for_quantity(order, item, selection.quantity)
            item.discount_type = data.discount_type
            item.discount_value = data.discount_value
            line_total = item.unit_price * item.qty
            if data.discount_type == "percent" and data.discount_value is not None:
                item.discount_amount = round(line_total * data.discount_value / 100, 2)
            elif data.discount_type == "fixed" and data.discount_value is not None:
                item.discount_amount = min(data.discount_value, line_total)
            else:
                item.discount_amount = 0.0

        await self._recompute_totals(order)
        await self.db.flush()
        return await self.get_order(order_id)

    async def set_item_comp(self, order_id: str, data: OrderItemCompRequest, comped_by_user_id: str) -> Order:
        """Mark (or unmark) items as 'on the house' — the item stays on the order and visible
        to the kitchen, but contributes nothing to the bill."""
        order = await self.get_order(order_id)
        if order.status in ("paid", "cancelled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a closed order")

        item_map = {item.id: item for item in order.items}
        for selection in data.items:
            item = item_map.get(selection.item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
            item = await self._split_item_for_quantity(order, item, selection.quantity)
            item.is_comped = data.comped
            item.comped_by = comped_by_user_id if data.comped else None

        await self._recompute_totals(order)
        await self.db.flush()
        return await self.get_order(order_id)

    async def delete_items(self, order_id: str, data: OrderItemDeleteRequest) -> Order:
        """Permanently remove one or more items. Items on an order still 'open' (not yet sent
        to the kitchen) can be removed freely; once submitted, a manager PIN + reason is
        required since the kitchen may already be preparing them."""
        order = await self.get_order(order_id)
        if order.status in ("paid", "cancelled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a closed order")

        if order.status != "open":
            if not data.override:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Manager PIN and reason are required to delete an item once the order has been submitted",
                )
            if not data.override.reason.strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A reason is required")
            await self._verify_manager_pin(order.location_id, data.override.manager_user_id, data.override.pin)

        item_map = {item.id: item for item in order.items}
        items_to_delete = []
        for selection in data.items:
            item = item_map.get(selection.item_id)
            if not item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
            item = await self._split_item_for_quantity(order, item, selection.quantity)
            items_to_delete.append(item)

        for item in items_to_delete:
            order.items.remove(item)
            await self.db.delete(item)
        await self.db.flush()

        await self._recompute_totals(order)
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self.get_order(order_id)

    async def _split_item_for_quantity(self, order: Order, item: OrderItem, quantity: int | None) -> OrderItem:
        """Splits off `quantity` units of `item` into a new row so a bulk action (guest
        tag/discount/comp/delete) can target a partial quantity while the rest of the line
        stays untouched. Returns the row the action should actually be applied to — either
        the new split-off row, or `item` itself when no partial split was requested."""
        if quantity is None or quantity >= item.qty:
            return item
        if quantity < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be at least 1")

        item.qty -= quantity
        split_item = OrderItem(
            order_id=order.id,
            menu_item_id=item.menu_item_id,
            menu_item_name=item.menu_item_name,
            qty=quantity,
            unit_price=item.unit_price,
            modifiers=item.modifiers,
            notes=item.notes,
            status=item.status,
            sort_order=item.sort_order,
            fire_course=item.fire_course,
            guest_number=item.guest_number,
        )
        self.db.add(split_item)
        await self.db.flush()
        # Keep the already-loaded collection in sync so this session's later reads
        # (recompute totals, delete-from-collection) see the new row immediately.
        order.items.append(split_item)
        return split_item

    async def _recalculate_totals(self, order: Order, tax_rate: float, item_total: float) -> None:
        order.subtotal = round(order.subtotal + item_total, 2)
        order.tax_amount = round(order.subtotal * tax_rate, 2)
        order.total = round(order.subtotal + order.tax_amount - order.discount_amount, 2)

    async def _recompute_totals(self, order: Order) -> None:
        """Full recompute from all non-cancelled items — used by bulk item actions
        (discount/comp/delete) where several items with distinct tax rates change at once."""
        menu_item_ids = {item.menu_item_id for item in order.items}
        tax_rates: dict[str, float] = {}
        if menu_item_ids:
            result = await self.db.execute(select(MenuItem.id, MenuItem.tax_rate).where(MenuItem.id.in_(menu_item_ids)))
            tax_rates = {row[0]: row[1] for row in result.all()}

        subtotal = 0.0
        tax_amount = 0.0
        for item in order.items:
            if item.status == "cancelled":
                continue
            net = 0.0 if item.is_comped else max(0.0, item.unit_price * item.qty - item.discount_amount)
            subtotal += net
            tax_amount += net * tax_rates.get(item.menu_item_id, 0.0)

        order.subtotal = round(subtotal, 2)
        order.tax_amount = round(tax_amount, 2)
        order.total = round(order.subtotal + order.tax_amount - order.discount_amount, 2)

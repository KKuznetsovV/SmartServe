"""Order service — lifecycle management for orders and items."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from smartserve_shared.security import verify_password
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Discount, Location, MenuCategory, MenuItem, ModifierGroup, Order, OrderItem, Table, User
from app.modules.ordering.schemas import (
    ApplyDiscountIn,
    AssignGuestsRequest,
    OrderCreate,
    OrderFireCourseRequest,
    OrderItemCompRequest,
    OrderItemCreate,
    OrderItemDeleteRequest,
    OrderItemDiscountRequest,
    OrderItemModifierIn,
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
    "split": {"cancelled"},
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

    async def apply_discount(self, order_id: str, data: ApplyDiscountIn, business_id: str | None = None) -> Order:
        """Apply a discount code to an order's total.

        `Discount` is owned by `catalog` (services/catalog) but this mutates `Order`, which
        `ordering` owns — so this logic lives here rather than in catalog's service, and reads
        the shared `discounts`/`locations` tables directly (same DB, read-only lookups; see
        docs/microservices-plan.md §4).
        """
        order = await self.get_order(order_id, business_id)
        if order.status not in {"open", "submitted"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot apply discount to this order")

        loc_result = await self.db.execute(select(Location).where(Location.id == order.location_id))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order location not found")

        discount_result = await self.db.execute(
            select(Discount).where(
                Discount.business_id == location.business_id,
                Discount.code == data.code.upper(),
                Discount.active.is_(True),
            )
        )
        discount = discount_result.scalar_one_or_none()
        if not discount:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount code not found or inactive")

        now = datetime.now(UTC)
        if discount.expires_at and discount.expires_at < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code has expired")
        if order.subtotal < discount.min_order_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order subtotal must be at least {discount.min_order_amount}",
            )

        if discount.type == "percent":
            discount_amount = round(order.subtotal * discount.value / 100, 2)
        else:
            discount_amount = min(discount.value, order.subtotal)

        order.discount_id = discount.id
        order.discount_amount = discount_amount
        order.total = round(order.subtotal + order.tax_amount - discount_amount, 2)
        await self.db.flush()
        return order

    async def list_orders(
        self,
        location_id: str,
        status_filter: str | None = None,
        limit: int = 100,
        offset: int = 0,
        business_id: str | None = None,
    ) -> list[Order]:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
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

    async def get_order(self, order_id: str, business_id: str | None = None) -> Order:
        q = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        if business_id is not None:
            q = q.join(Location, Order.location_id == Location.id).where(Location.business_id == business_id)
        result = await self.db.execute(q)
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def create_order(
        self, data: OrderCreate, created_by: str | None = None, business_id: str | None = None
    ) -> Order:
        if business_id is not None:
            await verify_location_owned(self.db, data.location_id, business_id, Location)

        if data.table_id:
            table_result = await self.db.execute(
                select(Table).where(Table.id == data.table_id, Table.location_id == data.location_id, Table.active)
            )
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
            created_by=created_by,
            status="open",
            subtotal=0.0,
            tax_amount=0.0,
            total=0.0,
        )
        self.db.add(order)
        await self.db.flush()
        return await self.get_order(order.id)

    async def _get_active_menu_item(self, menu_item_id: str) -> MenuItem:
        result = await self.db.execute(
            select(MenuItem)
            .where(MenuItem.id == menu_item_id, MenuItem.active, MenuItem.deleted_at.is_(None))
            .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
        )
        menu_item = result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found or unavailable")
        return menu_item

    def _snapshot_modifiers(self, menu_item: MenuItem, selections: list[OrderItemModifierIn]) -> list[dict]:
        by_id: dict[str, tuple] = {}
        for group in menu_item.modifier_groups:
            for modifier in group.modifiers:
                by_id[modifier.id] = (modifier, group)

        counts: dict[str, int] = {group.id: 0 for group in menu_item.modifier_groups}
        snapshots: list[dict] = []
        for selection in selections:
            found = by_id.get(selection.modifier_id)
            if found is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Modifier does not belong to this item",
                )
            modifier, group = found
            if not modifier.active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Modifier is inactive",
                )
            counts[group.id] += 1
            snapshots.append({"modifier_id": modifier.id, "name": modifier.name, "price_delta": modifier.price_delta})

        for group in menu_item.modifier_groups:
            selected = counts[group.id]
            if group.required and selected == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Required modifier group '{group.name}' has no selection",
                )
            if selected < group.min_select or selected > group.max_select:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Modifier group '{group.name}' requires between {group.min_select} and {group.max_select} selections",
                )
        return snapshots

    async def add_item(self, order_id: str, data: OrderItemCreate, business_id: str | None = None) -> OrderItem:
        order = await self.get_order(order_id, business_id)
        if order.status not in ("open", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add items to an order that is already being prepared",
            )

        menu_item = await self._get_active_menu_item(data.menu_item_id)
        if not menu_item.in_stock:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Menu item is out of stock")

        category_result = await self.db.execute(select(MenuCategory).where(MenuCategory.id == menu_item.category_id))
        category = category_result.scalar_one_or_none()

        snapshots = self._snapshot_modifiers(menu_item, data.modifiers)
        unit_price = menu_item.price + sum(m["price_delta"] for m in snapshots)
        fire_course = data.fire_course if data.fire_course is not None else menu_item.default_fire_course

        order_item = OrderItem(
            order_id=order_id,
            menu_item_id=data.menu_item_id,
            menu_item_name=menu_item.name,
            category_id=menu_item.category_id,
            category_name=category.name if category else None,
            qty=data.qty,
            unit_price=unit_price,
            modifiers=snapshots,
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

    async def update_item(
        self, order_id: str, item_id: str, data: OrderItemUpdate, business_id: str | None = None
    ) -> OrderItem:
        """Adjust quantity, notes, or modifiers/customization of an item already on the order."""
        order = await self.get_order(order_id, business_id)
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

        menu_item = None
        if item.menu_item_id:
            loaded = await self.db.execute(
                select(MenuItem)
                .where(MenuItem.id == item.menu_item_id)
                .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.modifiers))
            )
            menu_item = loaded.scalar_one_or_none()
        tax_rate = menu_item.tax_rate if menu_item else 0.0
        base_price = (
            menu_item.price if menu_item else item.unit_price - sum(m.get("price_delta", 0) for m in item.modifiers)
        )

        old_total = item.unit_price * item.qty

        if data.modifiers is not None:
            if not menu_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
            snapshots = self._snapshot_modifiers(menu_item, data.modifiers)
            item.modifiers = snapshots
            item.unit_price = base_price + sum(m["price_delta"] for m in snapshots)
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

    async def update_item_status(
        self, order_id: str, item_id: str, data: OrderItemStatusUpdate, business_id: str | None = None
    ) -> OrderItem:
        order = await self.get_order(order_id, business_id)
        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

        if data.status not in VALID_ITEM_TRANSITIONS.get(item.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition item from '{item.status}' to '{data.status}'",
            )

        item.status = data.status
        self._sync_kds_order_status(order)
        await self.db.flush()
        return item

    def _sync_kds_order_status(self, order: Order) -> None:
        """Roll the parent order status to match kitchen progress so customer displays
        show Received / Preparing / Ready instead of staying on 'submitted' forever.

        Reverse moves (ready → preparing when a later course is fired) are allowed here
        only — `transition_order` still uses the public one-way graph.
        """
        if order.status not in ("submitted", "preparing", "ready"):
            return
        active = [i for i in order.items if i.status not in ("cancelled", "held")]
        if not active:
            return
        statuses = {i.status for i in active}
        if "preparing" in statuses:
            target = "preparing"
        elif "pending" in statuses:
            target = "submitted"
        elif "ready" in statuses:
            target = "ready"
        else:
            return
        if target == order.status:
            return
        allowed = {
            "submitted": {"preparing", "ready"},
            "preparing": {"ready", "submitted"},
            "ready": {"preparing", "submitted"},
        }
        if target not in allowed.get(order.status, set()):
            return
        order.status = target
        order.updated_at = datetime.now(UTC)

    async def reorder_items(self, order_id: str, ids: list[str], business_id: str | None = None) -> None:
        if business_id is not None:
            await self.get_order(order_id, business_id)
        for order, item_id in enumerate(ids):
            await self.db.execute(
                update(OrderItem)
                .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
                .values(sort_order=order)
            )

    async def remove_item(self, order_id: str, item_id: str, business_id: str | None = None) -> None:
        order = await self.get_order(order_id, business_id)
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

    async def transition_order(self, order_id: str, new_status: str, business_id: str | None = None) -> Order:
        order = await self.get_order(order_id, business_id)
        if new_status not in VALID_ORDER_TRANSITIONS.get(order.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition order from '{order.status}' to '{new_status}'",
            )
        order.status = new_status
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        return order

    async def fire_course(self, order_id: str, data: OrderFireCourseRequest, business_id: str | None = None) -> Order:
        """Release all 'held' items of the given fire course so the kitchen can start them."""
        order = await self.get_order(order_id, business_id)
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
        self._sync_kds_order_status(order)
        await self.db.flush()
        return await self.get_order(order_id)

    async def assign_guests(self, order_id: str, data: AssignGuestsRequest, business_id: str | None = None) -> Order:
        """Optionally tag items with a guest number so a table's single order/check can
        still be organized or paid per-guest — this never creates a separate Order."""
        order = await self.get_order(order_id, business_id)
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

    async def apply_item_discount(
        self, order_id: str, data: OrderItemDiscountRequest, business_id: str | None = None
    ) -> Order:
        """Apply (or clear, when both fields are None) a manual %/fixed discount to one or
        more items on the order — distinct from the order-level discount-code feature."""
        order = await self.get_order(order_id, business_id)
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
                if data.discount_value > line_total:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Fixed discount cannot exceed the line total",
                    )
                item.discount_amount = data.discount_value
            else:
                item.discount_amount = 0.0

        await self._recompute_totals(order)
        await self.db.flush()
        return await self.get_order(order_id)

    async def set_item_comp(
        self, order_id: str, data: OrderItemCompRequest, comped_by_user_id: str, business_id: str | None = None
    ) -> Order:
        """Mark (or unmark) items as 'on the house' — the item stays on the order and visible
        to the kitchen, but contributes nothing to the bill."""
        order = await self.get_order(order_id, business_id)
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

    async def delete_items(self, order_id: str, data: OrderItemDeleteRequest, business_id: str | None = None) -> Order:
        """Permanently remove one or more items. Items on an order still 'open' (not yet sent
        to the kitchen) can be removed freely; once submitted, a manager PIN + reason is
        required since the kitchen may already be preparing them."""
        order = await self.get_order(order_id, business_id)
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

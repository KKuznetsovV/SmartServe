"""Order service — lifecycle management for orders and items."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.db.models import Order, OrderItem, MenuItem, Table
from app.schemas.order import OrderCreate, OrderItemCreate, OrderItemStatusUpdate


VALID_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "open":      {"submitted", "cancelled"},
    "submitted": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready":     {"served"},
    "served":    {"paid"},
    "paid":      set(),
    "cancelled": set(),
}

VALID_ITEM_TRANSITIONS: dict[str, set[str]] = {
    "pending":   {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready":     {"served"},
    "served":    set(),
    "cancelled": set(),
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_orders(self, location_id: str, status_filter: str | None = None) -> list[Order]:
        q = select(Order).where(Order.location_id == location_id).options(selectinload(Order.items))
        if status_filter:
            q = q.where(Order.status == status_filter)
        q = q.order_by(Order.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_order(self, order_id: str) -> Order:
        result = await self.db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def create_order(self, data: OrderCreate) -> Order:
        if data.table_id:
            table_result = await self.db.execute(
                select(Table).where(Table.id == data.table_id, Table.active == True)
            )
            if not table_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

        order = Order(
            location_id=data.location_id,
            table_id=data.table_id,
            channel=data.channel,
            notes=data.notes,
            status="open",
            subtotal=0.0,
            tax_amount=0.0,
            total=0.0,
        )
        self.db.add(order)
        await self.db.flush()
        return order

    async def add_item(self, order_id: str, data: OrderItemCreate) -> OrderItem:
        order = await self.get_order(order_id)
        if order.status not in ("open", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add items to an order that is already being prepared",
            )

        item_result = await self.db.execute(
            select(MenuItem).where(MenuItem.id == data.menu_item_id, MenuItem.active == True)
        )
        menu_item = item_result.scalar_one_or_none()
        if not menu_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found or unavailable")

        modifier_total = sum(m.price_delta for m in data.modifiers)
        unit_price = menu_item.price + modifier_total

        order_item = OrderItem(
            order_id=order_id,
            menu_item_id=data.menu_item_id,
            menu_item_name=menu_item.name,
            qty=data.qty,
            unit_price=unit_price,
            modifiers=[m.model_dump() for m in data.modifiers],
            notes=data.notes,
            status="pending",
        )
        self.db.add(order_item)

        # Recalculate order totals
        await self._recalculate_totals(order, menu_item.tax_rate, unit_price * data.qty)
        await self.db.flush()
        return order_item

    async def update_item_status(self, order_id: str, item_id: str, data: OrderItemStatusUpdate) -> OrderItem:
        result = await self.db.execute(
            select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
        )
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

    async def transition_order(self, order_id: str, new_status: str) -> Order:
        order = await self.get_order(order_id)
        if new_status not in VALID_ORDER_TRANSITIONS.get(order.status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition order from '{order.status}' to '{new_status}'",
            )
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return order

    async def _recalculate_totals(self, order: Order, tax_rate: float, item_total: float) -> None:
        order.subtotal = round(order.subtotal + item_total, 2)
        order.tax_amount = round(order.subtotal * tax_rate, 2)
        order.total = round(order.subtotal + order.tax_amount, 2)

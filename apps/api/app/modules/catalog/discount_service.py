"""Discount service — create/manage discount codes and apply them to orders."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Discount, Order
from app.modules.catalog.discount_schemas import ApplyDiscountIn, DiscountCreate, DiscountUpdate


class DiscountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DiscountCreate) -> Discount:
        if data.type not in {"percent", "fixed"}:
            raise HTTPException(status_code=400, detail="type must be 'percent' or 'fixed'")
        if data.type == "percent" and not (0 < data.value <= 100):
            raise HTTPException(status_code=400, detail="Percent discount value must be 1–100")

        existing = await self.db.execute(
            select(Discount).where(
                Discount.business_id == data.business_id,
                Discount.code == data.code.upper(),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Discount code already exists")

        discount = Discount(
            business_id=data.business_id,
            code=data.code.upper(),
            name=data.name,
            type=data.type,
            value=data.value,
            min_order_amount=data.min_order_amount,
            expires_at=data.expires_at,
        )
        self.db.add(discount)
        await self.db.flush()
        return discount

    async def list_by_business(self, business_id: str) -> list[Discount]:
        result = await self.db.execute(
            select(Discount).where(Discount.business_id == business_id).order_by(Discount.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, discount_id: str, data: DiscountUpdate) -> Discount:
        result = await self.db.execute(select(Discount).where(Discount.id == discount_id))
        discount = result.scalar_one_or_none()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        for field, val in data.model_dump(exclude_none=True).items():
            setattr(discount, field, val)
        await self.db.flush()
        return discount

    async def delete(self, discount_id: str) -> None:
        result = await self.db.execute(select(Discount).where(Discount.id == discount_id))
        discount = result.scalar_one_or_none()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        await self.db.delete(discount)

    async def apply_to_order(self, order_id: str, data: ApplyDiscountIn) -> Order:
        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status not in {"open", "submitted"}:
            raise HTTPException(status_code=400, detail="Cannot apply discount to this order")

        # Resolve the discount via business (through location)
        from app.db.models import Location  # noqa: PLC0415

        loc_result = await self.db.execute(select(Location).where(Location.id == order.location_id))
        location = loc_result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=404, detail="Order location not found")

        discount_result = await self.db.execute(
            select(Discount).where(
                Discount.business_id == location.business_id,
                Discount.code == data.code.upper(),
                Discount.active.is_(True),
            )
        )
        discount = discount_result.scalar_one_or_none()
        if not discount:
            raise HTTPException(status_code=404, detail="Discount code not found or inactive")

        now = datetime.now(UTC)
        if discount.expires_at and discount.expires_at < now:
            raise HTTPException(status_code=400, detail="Discount code has expired")
        if order.subtotal < discount.min_order_amount:
            raise HTTPException(
                status_code=400,
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

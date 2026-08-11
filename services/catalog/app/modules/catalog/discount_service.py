"""Discount service — create/manage discount codes.

Applying a discount to an order (which mutates `Order`, owned by `ordering`) lives in
`app.modules.ordering.service.OrderService.apply_discount` instead — see
docs/microservices-plan.md §4.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Discount
from app.modules.catalog.discount_schemas import DiscountCreate, DiscountUpdate


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

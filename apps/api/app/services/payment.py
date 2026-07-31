"""Payment service — abstract provider pattern, ready for Cardcom/Tranzila integration."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, Payment
from app.schemas.payment import PaymentCreate

VALID_PAYMENT_METHODS = {"cash", "card", "tap", "mobile", "voucher"}


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment(self, data: PaymentCreate) -> Payment:
        if data.method not in VALID_PAYMENT_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method. Allowed: {VALID_PAYMENT_METHODS}",
            )

        order_result = await self.db.execute(select(Order).where(Order.id == data.order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status == "paid":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already paid")

        # Abstract provider call — implement gateway here in step/06
        gateway_ref = None  # Future: await provider.charge(amount, method)

        payment = Payment(
            order_id=data.order_id,
            method=data.method,
            amount=data.amount,
            status="completed",  # Assume success for abstract layer
            gateway_ref=gateway_ref,
        )
        self.db.add(payment)

        # Mark order paid if fully covered
        if data.amount >= order.total:
            order.status = "paid"

        await self.db.flush()
        return payment

    async def get_payment(self, payment_id: str) -> Payment:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    async def list_by_order(self, order_id: str) -> list[Payment]:
        result = await self.db.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())

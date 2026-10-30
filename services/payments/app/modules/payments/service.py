"""Payment service — abstract provider pattern, ready for Cardcom/Tranzila integration."""

from fastapi import HTTPException, status
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, Order, Payment
from app.modules.payments.schemas import PaymentCreate

VALID_PAYMENT_METHODS = {"cash", "card", "tap", "mobile", "voucher"}
# Tolerate float rounding when comparing cumulative payments against the order total
PAID_IN_FULL_EPSILON = 0.01


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _owned_order(self, order_id: str, business_id: str) -> Order:
        order_result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        await verify_location_owned(self.db, order.location_id, business_id, Location)
        return order

    async def create_payment(self, data: PaymentCreate, business_id: str) -> tuple[Payment, bool, float]:
        if data.method not in VALID_PAYMENT_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method. Allowed: {VALID_PAYMENT_METHODS}",
            )
        if data.amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")
        if data.tip_amount < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tip amount cannot be negative")

        order = await self._owned_order(data.order_id, business_id)
        existing_paid = await self._completed_total(data.order_id)
        if existing_paid >= order.total - PAID_IN_FULL_EPSILON:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order already paid")

        # Abstract provider call — implement gateway here in step/06
        gateway_ref = None  # Future: await provider.charge(amount, method)

        payment = Payment(
            order_id=data.order_id,
            method=data.method,
            amount=data.amount,
            tip_amount=data.tip_amount,
            guest_number=data.guest_number,
            status="completed",  # Assume success for abstract layer
            gateway_ref=gateway_ref,
        )
        self.db.add(payment)
        await self.db.flush()

        # Fully-paid is decided from payment rows plus the read-only order total.
        # Ordering's payment.completed consumer is the only writer of orders.status.
        total_paid = await self._completed_total(data.order_id)
        fully_paid, remaining = self._settlement(order.total, total_paid)
        await self.db.flush()
        return payment, fully_paid, remaining

    async def _completed_total(self, order_id: str) -> float:
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0.0))
            .where(Payment.order_id == order_id)
            .where(Payment.status == "completed")
        )
        return float(paid_result.scalar_one())

    @staticmethod
    def _settlement(order_total: float, total_paid: float) -> tuple[bool, float]:
        fully_paid = total_paid >= order_total - PAID_IN_FULL_EPSILON
        remaining = 0.0 if fully_paid else max(0.0, round(order_total - total_paid, 2))
        return fully_paid, remaining

    async def get_payment(self, payment_id: str, business_id: str) -> Payment:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        await self._owned_order(payment.order_id, business_id)
        return payment

    async def list_by_order(self, order_id: str, business_id: str) -> list[Payment]:
        await self._owned_order(order_id, business_id)
        result = await self.db.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())

"""Payment service — abstract provider pattern, ready for Cardcom/Tranzila integration."""

from decimal import Decimal

from fastapi import HTTPException, status
from smartserve_shared.money import money
from smartserve_shared.security import verify_password
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, Order, OrderItem, Payment, User
from app.modules.payments.schemas import PaymentCreate, PaymentRefundIn

VALID_PAYMENT_METHODS = {"cash", "card", "tap", "mobile", "voucher"}
PAYABLE_STATUSES = {"submitted", "preparing", "ready", "served"}
CAPPED_METHODS = {"card", "tap", "mobile", "voucher"}
UNSENT_ITEM_STATUSES = {"held"}


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

    async def _lock_order(self, order_id: str) -> None:
        conn = await self.db.connection()
        if conn.dialect.name != "postgresql":
            return
        await self.db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:order_id))"), {"order_id": order_id})

    async def create_payment(
        self, data: PaymentCreate, business_id: str, idempotency_key: str | None = None
    ) -> tuple[Payment, bool, Decimal, bool]:
        if data.method not in VALID_PAYMENT_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment method. Allowed: {VALID_PAYMENT_METHODS}",
            )
        requested = money(data.amount)
        tip_amount = money(data.tip_amount)
        if requested <= money(0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")
        if tip_amount < money(0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tip amount cannot be negative")

        await self._lock_order(data.order_id)

        if idempotency_key:
            existing = await self.db.execute(
                select(Payment).where(
                    Payment.order_id == data.order_id,
                    Payment.idempotency_key == idempotency_key,
                )
            )
            replay = existing.scalar_one_or_none()
            if replay is not None:
                total_paid = await self._completed_total(data.order_id)
                order = await self._owned_order(data.order_id, business_id)
                fully_paid, remaining = self._settlement(order.total, total_paid)
                return replay, fully_paid, remaining, False

        order = await self._owned_order(data.order_id, business_id)
        await self._assert_payable(order)

        existing_paid = await self._completed_total(data.order_id)
        remaining_before = money(order.total) - existing_paid
        if remaining_before <= money(0):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already paid")

        tendered = None
        change_due = money(0)
        applied = requested
        if data.method == "cash" and requested > remaining_before:
            tendered = requested
            applied = remaining_before
            change_due = money(tendered - applied)
        elif data.method in CAPPED_METHODS and requested > remaining_before:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Amount exceeds the remaining balance",
            )

        payment = Payment(
            order_id=data.order_id,
            method=data.method,
            amount=applied,
            tip_amount=tip_amount,
            tendered=tendered,
            change_due=change_due,
            guest_number=data.guest_number,
            status="completed",
            idempotency_key=idempotency_key,
        )
        self.db.add(payment)
        await self.db.flush()

        total_paid = await self._completed_total(data.order_id)
        fully_paid, remaining = self._settlement(order.total, total_paid)
        return payment, fully_paid, remaining, True

    async def _assert_payable(self, order: Order) -> None:
        if order.status not in PAYABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only submitted, preparing, ready or served orders can be paid",
            )
        if money(order.total) <= money(0):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order total must be greater than zero",
            )
        unsent = await self.db.execute(
            select(OrderItem.id).where(
                OrderItem.order_id == order.id,
                OrderItem.status.in_(UNSENT_ITEM_STATUSES),
            )
        )
        if unsent.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot pay while items are still unsent",
            )

    async def refund_payment(
        self, payment_id: str, data: PaymentRefundIn, business_id: str
    ) -> tuple[Payment, bool, Decimal]:
        if not data.reason.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A reason is required")
        original = await self.get_payment(payment_id, business_id)
        if original.amount <= money(0) or original.refund_of_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a captured payment can be refunded")
        await self._lock_order(original.order_id)
        await self._verify_manager_pin(original.order_id, data.manager_user_id, data.pin)

        already = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.refund_of_id == original.id,
                Payment.status == "completed",
            )
        )
        already_refunded = money(already.scalar_one())
        refundable = money(original.amount + already_refunded)
        if refundable <= money(0):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment has already been refunded")

        refund = Payment(
            order_id=original.order_id,
            method=original.method,
            amount=money(-refundable),
            tip_amount=money(0),
            status="completed",
            refund_of_id=original.id,
        )
        self.db.add(refund)
        await self.db.flush()
        order = await self._owned_order(original.order_id, business_id)
        total_paid = await self._completed_total(original.order_id)
        fully_paid, remaining = self._settlement(order.total, total_paid)
        return refund, fully_paid, remaining

    async def _verify_manager_pin(self, order_id: str, manager_user_id: str, pin: str) -> User:
        order = await self.db.get(Order, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager PIN")
        loc_result = await self.db.execute(select(Location).where(Location.id == order.location_id))
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

    async def _completed_total(self, order_id: str) -> Decimal:
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.order_id == order_id)
            .where(Payment.status == "completed")
        )
        return money(paid_result.scalar_one())

    @staticmethod
    def _settlement(order_total: object, total_paid: object) -> tuple[bool, Decimal]:
        order_total = money(order_total)
        total_paid = money(total_paid)
        fully_paid = total_paid >= order_total
        remaining = money(0) if fully_paid else money(order_total - total_paid)
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

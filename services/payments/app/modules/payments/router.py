from fastapi import Depends, Header, status
from fastapi.responses import JSONResponse
from smartserve_shared.outbox import enqueue
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_staff
from app.db.models import Outbox, User
from app.db.session import DbSession
from app.modules.payments.schemas import PaymentCreate, PaymentOut, PaymentRefundIn
from app.modules.payments.service import PaymentService

router = APIRouter()


def _payment_out(payment, fully_paid: bool, remaining) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    return out.model_copy(update={"order_fully_paid": fully_paid, "remaining": remaining})


@router.post("/payments")
async def create_payment(
    data: PaymentCreate,
    db: DbSession,
    current_user: User = Depends(require_staff),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    payment, fully_paid, remaining, created = await PaymentService(db).create_payment(
        data, current_user.business_id, idempotency_key
    )
    if created and fully_paid:
        await enqueue(
            db,
            Outbox,
            "payment.completed",
            {
                "paymentId": payment.id,
                "orderId": payment.order_id,
                "amount": payment.amount,
                "method": payment.method,
                "businessId": current_user.business_id,
            },
            business_id=current_user.business_id,
        )
    out = _payment_out(payment, fully_paid, remaining)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        content=out.model_dump(by_alias=True, mode="json"),
    )


@router.post("/payments/{payment_id}/refund", response_model=PaymentOut)
async def refund_payment(
    payment_id: str,
    data: PaymentRefundIn,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    refund, fully_paid, remaining = await PaymentService(db).refund_payment(payment_id, data, current_user.business_id)
    await enqueue(
        db,
        Outbox,
        "payment.refunded",
        {
            "paymentId": refund.id,
            "refundOfId": payment_id,
            "orderId": refund.order_id,
            "amount": refund.amount,
            "businessId": current_user.business_id,
        },
        business_id=current_user.business_id,
    )
    return _payment_out(refund, fully_paid, remaining)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: str,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await PaymentService(db).get_payment(payment_id, current_user.business_id)


@router.get("/orders/{order_id}/payments", response_model=list[PaymentOut])
async def list_order_payments(
    order_id: str,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await PaymentService(db).list_by_order(order_id, current_user.business_id)

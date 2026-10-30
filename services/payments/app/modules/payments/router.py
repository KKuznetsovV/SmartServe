from fastapi import Depends
from smartserve_shared.outbox import enqueue
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_staff
from app.db.models import Outbox, User
from app.db.session import DbSession
from app.modules.payments.schemas import PaymentCreate, PaymentOut
from app.modules.payments.service import PaymentService

router = APIRouter()


@router.post("/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    data: PaymentCreate,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    payment, fully_paid, remaining = await PaymentService(db).create_payment(data, current_user.business_id)
    if fully_paid:
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
    out = PaymentOut.model_validate(payment)
    return out.model_copy(update={"order_fully_paid": fully_paid, "remaining": remaining})


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

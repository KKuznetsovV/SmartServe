from fastapi import Depends, Request
from smartserve_shared import mq
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_staff
from app.db.models import User
from app.db.session import DbSession
from app.modules.payments.schemas import PaymentCreate, PaymentOut
from app.modules.payments.service import PaymentService

router = APIRouter()


@router.post("/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    data: PaymentCreate,
    request: Request,
    db: DbSession,
    _: User = Depends(require_staff),
):
    payment, order = await PaymentService(db).create_payment(data)
    if order.status == "paid":
        await mq.publish(
            request.app.state.mq_connection,
            "payment.completed",
            {
                "paymentId": payment.id,
                "orderId": payment.order_id,
                "amount": payment.amount,
                "method": payment.method,
            },
        )
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: str,
    db: DbSession,
    _: User = Depends(require_staff),
):
    return await PaymentService(db).get_payment(payment_id)


@router.get("/orders/{order_id}/payments", response_model=list[PaymentOut])
async def list_order_payments(
    order_id: str,
    db: DbSession,
    _: User = Depends(require_staff),
):
    return await PaymentService(db).list_by_order(order_id)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User
from app.services.payment import PaymentService
from app.schemas.payment import PaymentOut, PaymentCreate
from app.api.v1.deps import require_staff

router = APIRouter()


@router.post("/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    return await PaymentService(db).create_payment(data)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    return await PaymentService(db).get_payment(payment_id)


@router.get("/orders/{order_id}/payments", response_model=list[PaymentOut])
async def list_order_payments(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    return await PaymentService(db).list_by_order(order_id)

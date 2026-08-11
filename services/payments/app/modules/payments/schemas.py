from datetime import datetime

from app.schemas.base import BaseSchema as BaseModel


class PaymentOut(BaseModel):
    id: str
    order_id: str
    method: str
    amount: float
    tip_amount: float = 0.0
    guest_number: int | None = None
    status: str
    gateway_ref: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    order_id: str
    method: str
    amount: float
    tip_amount: float = 0.0
    guest_number: int | None = None

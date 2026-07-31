from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentOut(BaseModel):
    id: str
    order_id: str
    method: str
    amount: float
    status: str
    gateway_ref: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    order_id: str
    method: str
    amount: float

from datetime import datetime
from decimal import Decimal

from smartserve_shared.money import Money, OptionalMoney
from smartserve_shared.schemas import BaseSchema as BaseModel


class PaymentOut(BaseModel):
    id: str
    order_id: str
    method: str
    amount: Money
    tip_amount: Money = Decimal("0.00")
    tendered: OptionalMoney = None
    change_due: Money = Decimal("0.00")
    guest_number: int | None = None
    status: str
    gateway_ref: str | None = None
    created_at: datetime
    order_fully_paid: bool | None = None
    remaining: OptionalMoney = None

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    order_id: str
    method: str
    amount: Money
    tip_amount: Money = Decimal("0.00")
    guest_number: int | None = None


class PaymentRefundIn(BaseModel):
    manager_user_id: str
    pin: str
    reason: str

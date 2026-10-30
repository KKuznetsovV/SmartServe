from datetime import datetime
from decimal import Decimal

from smartserve_shared.money import Money, OptionalMoney
from smartserve_shared.schemas import BaseSchema as BaseModel


class DiscountCreate(BaseModel):
    business_id: str
    code: str
    name: str
    type: str = "percent"  # percent | fixed
    value: Money
    min_order_amount: Money = Decimal("0.00")
    expires_at: datetime | None = None


class DiscountUpdate(BaseModel):
    name: str | None = None
    value: OptionalMoney = None
    min_order_amount: OptionalMoney = None
    active: bool | None = None
    expires_at: datetime | None = None


class DiscountOut(BaseModel):
    id: str
    business_id: str
    code: str
    name: str
    type: str
    value: Money
    min_order_amount: Money
    active: bool
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplyDiscountIn(BaseModel):
    code: str

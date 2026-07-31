from datetime import datetime

from app.schemas.base import BaseSchema as BaseModel


class DiscountCreate(BaseModel):
    business_id: str
    code: str
    name: str
    type: str = "percent"  # percent | fixed
    value: float
    min_order_amount: float = 0.0
    expires_at: datetime | None = None


class DiscountUpdate(BaseModel):
    name: str | None = None
    value: float | None = None
    min_order_amount: float | None = None
    active: bool | None = None
    expires_at: datetime | None = None


class DiscountOut(BaseModel):
    id: str
    business_id: str
    code: str
    name: str
    type: str
    value: float
    min_order_amount: float
    active: bool
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplyDiscountIn(BaseModel):
    code: str

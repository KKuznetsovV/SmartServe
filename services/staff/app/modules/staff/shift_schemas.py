from datetime import datetime
from decimal import Decimal

from smartserve_shared.money import Money, OptionalMoney
from smartserve_shared.schemas import BaseSchema as BaseModel


class ShiftOpen(BaseModel):
    opening_cash: Money = Decimal("0.00")
    notes: str | None = None


class ShiftClose(BaseModel):
    closing_cash: Money = Decimal("0.00")
    notes: str | None = None


class ShiftOut(BaseModel):
    id: str
    location_id: str
    opened_by: str
    closed_by: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: Money
    closing_cash: OptionalMoney = None
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}

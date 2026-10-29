from datetime import datetime

from smartserve_shared.schemas import BaseSchema as BaseModel


class ShiftOpen(BaseModel):
    opening_cash: float = 0.0
    notes: str | None = None


class ShiftClose(BaseModel):
    closing_cash: float = 0.0
    notes: str | None = None


class ShiftOut(BaseModel):
    id: str
    location_id: str
    opened_by: str
    closed_by: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    opening_cash: float
    closing_cash: float | None = None
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}

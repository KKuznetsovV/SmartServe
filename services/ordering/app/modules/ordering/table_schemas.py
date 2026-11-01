from datetime import datetime

from smartserve_shared.money import Money
from smartserve_shared.schemas import BaseSchema as BaseModel


class TableOpenOrderOut(BaseModel):
    id: str
    status: str
    guest_count: int | None = None
    seated_since: datetime
    total: Money


class TableOut(BaseModel):
    id: str
    location_id: str
    name: str
    capacity: int
    section: str | None = None
    pos_x: float
    pos_y: float
    active: bool
    floor_state: str = "free"
    open_order: TableOpenOrderOut | None = None

    model_config = {"from_attributes": True}


class TableCreate(BaseModel):
    location_id: str
    name: str
    capacity: int = 4
    section: str | None = None
    pos_x: float = 0.0
    pos_y: float = 0.0


class TableUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    section: str | None = None
    pos_x: float | None = None
    pos_y: float | None = None
    active: bool | None = None

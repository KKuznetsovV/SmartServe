from app.schemas.base import BaseSchema as BaseModel


class TableOut(BaseModel):
    id: str
    location_id: str
    name: str
    capacity: int
    section: str | None = None
    pos_x: float
    pos_y: float
    active: bool

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

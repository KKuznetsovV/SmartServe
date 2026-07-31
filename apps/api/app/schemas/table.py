from pydantic import BaseModel
from typing import Optional


class TableOut(BaseModel):
    id: str
    location_id: str
    name: str
    capacity: int
    section: Optional[str] = None
    pos_x: float
    pos_y: float
    active: bool

    model_config = {"from_attributes": True}


class TableCreate(BaseModel):
    location_id: str
    name: str
    capacity: int = 4
    section: Optional[str] = None
    pos_x: float = 0.0
    pos_y: float = 0.0


class TableUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    section: Optional[str] = None
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    active: Optional[bool] = None

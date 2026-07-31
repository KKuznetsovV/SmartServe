from pydantic import BaseModel
from typing import Optional


class PrinterOut(BaseModel):
    id: str
    location_id: str
    name: str
    type: str
    ip: Optional[str] = None
    port: int
    active: bool

    model_config = {"from_attributes": True}


class PrinterCreate(BaseModel):
    location_id: str
    name: str
    type: str = "receipt"  # receipt | kitchen | label
    ip: Optional[str] = None
    port: int = 9100


class PrinterUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    active: Optional[bool] = None


class PrinterRouteCreate(BaseModel):
    printer_id: str
    category_id: str

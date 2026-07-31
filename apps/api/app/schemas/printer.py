from app.schemas.base import BaseSchema as BaseModel


class PrinterOut(BaseModel):
    id: str
    location_id: str
    name: str
    type: str
    ip: str | None = None
    port: int
    active: bool

    model_config = {"from_attributes": True}


class PrinterCreate(BaseModel):
    location_id: str
    name: str
    type: str = "receipt"  # receipt | kitchen | label
    ip: str | None = None
    port: int = 9100


class PrinterUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    ip: str | None = None
    port: int | None = None
    active: bool | None = None


class PrinterRouteCreate(BaseModel):
    printer_id: str
    category_id: str


class PrinterRouteOut(BaseModel):
    printer_id: str
    category_id: str

    model_config = {"from_attributes": True}

from app.schemas.base import BaseSchema as BaseModel


class BusinessOut(BaseModel):
    id: str
    name: str
    tax_id: str | None = None
    country: str
    currency: str
    created_at: str

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    currency: str | None = None


class LocationOut(BaseModel):
    id: str
    business_id: str
    name: str
    address: str | None = None
    timezone: str
    language: str
    active: bool

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "Asia/Jerusalem"
    language: str = "he"


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    language: str | None = None
    active: bool | None = None

from pydantic import BaseModel, field_validator
from typing import Optional


class BusinessOut(BaseModel):
    id: str
    name: str
    tax_id: Optional[str] = None
    country: str
    currency: str
    created_at: str

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    currency: Optional[str] = None


class LocationOut(BaseModel):
    id: str
    business_id: str
    name: str
    address: Optional[str] = None
    timezone: str
    language: str
    active: bool

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    address: Optional[str] = None
    timezone: str = "Asia/Jerusalem"
    language: str = "he"


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    active: Optional[bool] = None

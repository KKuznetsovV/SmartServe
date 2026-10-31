from datetime import datetime, time
from decimal import Decimal

from pydantic import Field, field_validator
from smartserve_shared.business_day import DEFAULT_BUSINESS_DAY_CUTOFF, parse_cutoff
from smartserve_shared.money import OptionalRate, Rate
from smartserve_shared.roles import Role
from smartserve_shared.schemas import BaseSchema as BaseModel


class BusinessOut(BaseModel):
    id: str
    name: str
    tax_id: str | None = None
    country: str
    currency: str
    vat_rate: Rate = Decimal("0.18")
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    currency: str | None = None
    vat_rate: Rate | None = Field(None, ge=0, le=1)


class LocationOut(BaseModel):
    id: str
    business_id: str
    name: str
    address: str | None = None
    timezone: str
    business_day_cutoff: time = DEFAULT_BUSINESS_DAY_CUTOFF
    language: str
    vat_rate: OptionalRate = None
    active: bool

    model_config = {"from_attributes": True}

    @field_validator("business_day_cutoff", mode="before")
    @classmethod
    def _cutoff_out(cls, value: object) -> time:
        return parse_cutoff(value if isinstance(value, (time, str)) else None)


class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "Asia/Jerusalem"
    business_day_cutoff: time = DEFAULT_BUSINESS_DAY_CUTOFF
    language: str = "he"
    vat_rate: OptionalRate = Field(None, ge=0, le=1)

    @field_validator("business_day_cutoff", mode="before")
    @classmethod
    def _cutoff_create(cls, value: object) -> time:
        return parse_cutoff(value if isinstance(value, (time, str)) else None)


class UserOut(BaseModel):
    id: str
    business_id: str
    email: str | None = None
    name: str
    role: Role
    language: str
    active: bool

    model_config = {"from_attributes": True}


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    business_day_cutoff: time | None = None
    language: str | None = None
    vat_rate: OptionalRate = Field(None, ge=0, le=1)
    active: bool | None = None

    @field_validator("business_day_cutoff", mode="before")
    @classmethod
    def _cutoff_update(cls, value: object) -> time | None:
        if value is None:
            return None
        return parse_cutoff(value if isinstance(value, (time, str)) else None)

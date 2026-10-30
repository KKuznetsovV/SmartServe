import re

from pydantic import EmailStr, field_validator
from smartserve_shared.roles import Role
from smartserve_shared.schemas import BaseSchema as BaseModel

_PIN_RE = re.compile(r"^\d{4,6}$")


def _normalize_email(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped.lower() or None
    return str(value).lower()


def _normalize_pin(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not _PIN_RE.fullmatch(value):
        raise ValueError("PIN must be 4 to 6 digits")
    return value


def _normalize_password(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    return value


class UserOut(BaseModel):
    id: str
    business_id: str
    email: str | None = None
    name: str
    role: Role
    language: str
    active: bool

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    email: EmailStr | None = None
    name: str
    role: Role = "waiter"
    language: str = "he"
    password: str | None = None
    pin: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: object) -> str | None:
        return _normalize_email(value)

    @field_validator("pin", mode="before")
    @classmethod
    def validate_pin(cls, value: object) -> str | None:
        return _normalize_pin(value)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value: object) -> str | None:
        return _normalize_password(value)


class StaffUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None
    language: str | None = None
    active: bool | None = None
    pin: str | None = None

    @field_validator("pin", mode="before")
    @classmethod
    def validate_pin(cls, value: object) -> str | None:
        return _normalize_pin(value)

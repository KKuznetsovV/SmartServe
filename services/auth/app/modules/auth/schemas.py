"""Request/response schemas for the auth endpoints."""

from pydantic import EmailStr, field_validator
from smartserve_shared.roles import Role
from smartserve_shared.schemas import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class PinLoginRequest(BaseSchema):
    location_id: str
    user_id: str
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, value: str) -> str:
        if not value.isdigit() or not 4 <= len(value) <= 6:
            raise ValueError("PIN must be 4 to 6 digits")
        return value


class PinStaffOut(BaseSchema):
    """Minimal staff info for the PIN-login user picker — no email/pin data exposed."""

    id: str
    name: str
    role: Role

    model_config = {"from_attributes": True}


class TokenResponse(BaseSchema):
    access_token: str
    expires_in: int
    token_type: str = "bearer"

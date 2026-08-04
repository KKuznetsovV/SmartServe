"""Request/response schemas for the auth endpoints."""

from pydantic import EmailStr

from app.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class PinLoginRequest(BaseSchema):
    location_id: str
    pin: str


class PinStaffOut(BaseSchema):
    """Minimal staff info for the PIN-login user picker — no email/pin data exposed."""

    id: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseSchema):
    refresh_token: str

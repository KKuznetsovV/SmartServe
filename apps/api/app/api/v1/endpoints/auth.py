from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router_base import APIRouter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.models import User
from app.db.session import get_db

router = APIRouter()
bearer = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PinLoginRequest(BaseModel):
    location_id: str
    pin: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email, User.active))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    extra = {"business_id": user.business_id, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
        expires_in=900,
    )


@router.post("/pin", response_model=TokenResponse)
async def pin_login(body: PinLoginRequest, db: AsyncSession = Depends(get_db)):
    # TODO: add Redis-based rate limiting (MAX_PIN_ATTEMPTS) in step/02
    result = await db.execute(select(User).where(User.active))
    users = result.scalars().all()
    matched = next((u for u in users if u.pin_hash and verify_password(body.pin, u.pin_hash)), None)
    if not matched:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

    extra = {"business_id": matched.business_id, "role": matched.role}
    return TokenResponse(
        access_token=create_access_token(matched.id, extra),
        refresh_token=create_refresh_token(matched.id),
        expires_in=900,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    extra: dict = {}
    return TokenResponse(
        access_token=create_access_token(payload["sub"], extra),
        refresh_token=create_refresh_token(payload["sub"]),
        expires_in=900,
    )


@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "businessId": user.business_id,
        "language": user.language,
    }

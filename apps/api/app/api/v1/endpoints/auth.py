from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router_base import APIRouter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.models import Location, User
from app.db.session import get_db
from app.schemas.base import BaseSchema

router = APIRouter()
bearer = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class PinLoginRequest(BaseSchema):
    location_id: str
    pin: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseSchema):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("20/minute")
async def pin_login(request: Request, body: PinLoginRequest, db: AsyncSession = Depends(get_db)):
    # Scope PIN matching to the location's business — prevents cross-tenant login
    loc_result = await db.execute(select(Location).where(Location.id == body.location_id, Location.active))
    location = loc_result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

    result = await db.execute(
        select(User).where(User.business_id == location.business_id, User.active, User.pin_hash.is_not(None))
    )
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
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    # Reload the user so refreshed tokens keep claims and deactivated users are rejected
    result = await db.execute(select(User).where(User.id == payload["sub"], User.active))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    extra = {"business_id": user.business_id, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
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

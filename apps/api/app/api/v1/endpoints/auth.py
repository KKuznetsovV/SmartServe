from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router_base import APIRouter
from app.db.session import get_db
from app.schemas.auth import LoginRequest, PinLoginRequest, RefreshRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter()
bearer = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).login(body.email, body.password)


@router.post("/pin", response_model=TokenResponse)
@limiter.limit("20/minute")
async def pin_login(request: Request, body: PinLoginRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).pin_login(body.location_id, body.pin)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).refresh(body.refresh_token)


@router.get("/me")
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).get_user_profile(credentials.credentials)

from fastapi import Depends, Header, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from smartserve_shared.routing import APIRouter

from app.db.session import DbSession
from app.modules.auth.device_service import DeviceService
from app.modules.auth.schemas import LoginRequest, PinLoginRequest, PinStaffOut, RefreshRequest, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter()
bearer = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: DbSession):
    return await AuthService(db).login(body.email, body.password)


@router.get("/pin/staff", response_model=list[PinStaffOut])
@limiter.limit("30/minute")
async def pin_staff(
    request: Request,
    db: DbSession,
    location_id: str = Query(alias="locationId"),
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
):
    """Staff-picker list for the PIN-login screen (name + role only). Requires a paired device."""
    await DeviceService(db).authenticate(x_device_token, location_id)
    return await AuthService(db).list_pin_staff(location_id)


@router.post("/pin", response_model=TokenResponse)
@limiter.limit("20/minute")
async def pin_login(
    request: Request,
    body: PinLoginRequest,
    db: DbSession,
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
):
    await DeviceService(db).authenticate(x_device_token, body.location_id)
    return await AuthService(db).pin_login(body.location_id, body.user_id, body.pin)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession):
    return await AuthService(db).refresh(body.refresh_token)


@router.get("/me")
async def get_me(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    return await AuthService(db).get_user_profile(credentials.credentials)

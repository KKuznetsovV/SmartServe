from fastapi import Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from smartserve_shared.app_factory import limiter
from smartserve_shared.routing import APIRouter

from app.db.session import DbSession
from app.modules.auth.cookies import COOKIE_NAME, clear_refresh_cookie, set_refresh_cookie
from app.modules.auth.device_service import DeviceService
from app.modules.auth.refresh_store import revoke_presented
from app.modules.auth.schemas import LoginRequest, PinLoginRequest, PinStaffOut, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter()
bearer = HTTPBearer()


def _redis(request: Request):
    return getattr(request.app.state, "redis", None)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    redis = _redis(request)
    tokens, refresh = await AuthService(db, redis).login(body.email, body.password)
    await revoke_presented(redis, refresh_token)
    set_refresh_cookie(response, refresh)
    return tokens


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
    return await AuthService(db, _redis(request)).list_pin_staff(location_id)


@router.post("/pin", response_model=TokenResponse)
@limiter.limit("20/minute")
async def pin_login(
    request: Request,
    response: Response,
    body: PinLoginRequest,
    db: DbSession,
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    redis = _redis(request)
    device = await DeviceService(db).authenticate(x_device_token, body.location_id)
    tokens, refresh = await AuthService(db, redis).pin_login(
        body.location_id, body.user_id, body.pin, device_id=device.id
    )
    await revoke_presented(redis, refresh_token)
    set_refresh_cookie(response, refresh)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    tokens, refresh_value = await AuthService(db, _redis(request)).refresh(refresh_token)
    set_refresh_cookie(response, refresh_value)
    return tokens


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    await revoke_presented(_redis(request), refresh_token)
    clear_refresh_cookie(response)


@router.get("/me")
async def get_me(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    return await AuthService(db).get_user_profile(credentials.credentials)

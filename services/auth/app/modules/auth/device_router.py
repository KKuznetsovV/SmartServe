from fastapi import Depends, Header
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.auth.device_schemas import DeviceCreate, DeviceOut, DeviceRegisterOut
from app.modules.auth.device_service import DeviceService

router = APIRouter()


@router.post("/locations/{location_id}/devices", response_model=DeviceRegisterOut, status_code=201)
async def register_device(
    location_id: str,
    data: DeviceCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    device, raw = await DeviceService(db).register(location_id, data, current_user)
    payload = DeviceOut.model_validate(device).model_dump()
    return DeviceRegisterOut(**payload, token=raw)


@router.get("/locations/{location_id}/devices", response_model=list[DeviceOut])
async def list_devices(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await DeviceService(db).list_for_location(location_id, current_user)


@router.post("/devices/{device_id}/revoke", response_model=DeviceOut)
async def revoke_device(
    device_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await DeviceService(db).revoke(device_id, current_user)


@router.get("/devices/current", response_model=DeviceOut)
async def current_device(
    db: DbSession,
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
):
    return await DeviceService(db).resolve(x_device_token)

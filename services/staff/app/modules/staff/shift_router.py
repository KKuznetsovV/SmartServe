from fastapi import Depends
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import get_current_user, require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.staff.shift_schemas import ShiftClose, ShiftOpen, ShiftOut
from app.modules.staff.shift_service import ShiftService

router = APIRouter()


@router.post("/locations/{location_id}/shifts/open", response_model=ShiftOut, status_code=201)
async def open_shift(
    location_id: str,
    data: ShiftOpen,
    db: DbSession,
    user: User = Depends(require_manager),
):
    return await ShiftService(db).open_shift(user.id, location_id, data, user.business_id)


@router.post("/shifts/{shift_id}/close", response_model=ShiftOut)
async def close_shift(
    shift_id: str,
    data: ShiftClose,
    db: DbSession,
    user: User = Depends(require_manager),
):
    return await ShiftService(db).close_shift(shift_id, user.id, data, user.business_id)


@router.get("/locations/{location_id}/shifts/current", response_model=ShiftOut | None)
async def get_current_shift(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await ShiftService(db).get_current(location_id, current_user.business_id)


@router.get("/locations/{location_id}/shifts", response_model=list[ShiftOut])
async def list_shifts(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return await ShiftService(db).list_shifts(location_id, current_user.business_id)

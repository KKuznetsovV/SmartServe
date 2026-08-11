from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.modules.staff.shift_schemas import ShiftClose, ShiftOpen, ShiftOut
from app.modules.staff.shift_service import ShiftService

router = APIRouter()


@router.post("/locations/{location_id}/shifts/open", response_model=ShiftOut, status_code=201)
async def open_shift(
    location_id: str,
    data: ShiftOpen,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    return await ShiftService(db).open_shift(user.id, location_id, data)


@router.post("/shifts/{shift_id}/close", response_model=ShiftOut)
async def close_shift(
    shift_id: str,
    data: ShiftClose,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_manager),
):
    return await ShiftService(db).close_shift(shift_id, user.id, data)


@router.get("/locations/{location_id}/shifts/current", response_model=ShiftOut | None)
async def get_current_shift(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ShiftService(db).get_current(location_id)


@router.get("/locations/{location_id}/shifts", response_model=list[ShiftOut])
async def list_shifts(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await ShiftService(db).list_shifts(location_id)

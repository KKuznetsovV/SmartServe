from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.db.models import User
from app.db.session import get_db
from app.schemas.staff import StaffCreate, StaffUpdate, UserOut
from app.services.staff import StaffService

router = APIRouter()


@router.post("/staff", response_model=UserOut, status_code=201)
async def create_staff(
    data: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    return await StaffService(db).create_staff(current_user.business_id, data)


@router.get("/staff/{user_id}", response_model=UserOut)
async def get_staff(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await StaffService(db).get_user(user_id)


@router.patch("/staff/{user_id}", response_model=UserOut)
async def update_staff(
    user_id: str,
    data: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await StaffService(db).update_staff(user_id, data)

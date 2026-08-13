from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.api.v1.router_base import APIRouter
from app.core import mq
from app.db.models import User
from app.db.session import get_db
from app.modules.staff.schemas import StaffCreate, StaffUpdate, UserOut
from app.modules.staff.service import StaffService

router = APIRouter()


@router.post("/staff", response_model=UserOut, status_code=201)
async def create_staff(
    data: StaffCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    staff = await StaffService(db).create_staff(current_user.business_id, data)
    await mq.publish(
        request.app.state.mq_connection,
        "staff.created",
        {"userId": staff.id, "businessId": staff.business_id, "name": staff.name, "role": staff.role},
    )
    return staff


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    staff = await StaffService(db).update_staff(user_id, data)
    await mq.publish(
        request.app.state.mq_connection,
        "staff.updated",
        {"userId": staff.id, "businessId": staff.business_id, "name": staff.name, "role": staff.role},
    )
    return staff

from fastapi import Depends
from smartserve_shared.outbox import enqueue
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_manager
from app.db.models import Outbox, User
from app.db.session import DbSession
from app.modules.staff.schemas import StaffCreate, StaffUpdate, UserOut
from app.modules.staff.service import StaffService

router = APIRouter()


@router.post("/staff", response_model=UserOut, status_code=201)
async def create_staff(
    data: StaffCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    staff = await StaffService(db).create_staff(current_user, data)
    await enqueue(
        db,
        Outbox,
        "staff.created",
        {
            "userId": staff.id,
            "businessId": current_user.business_id,
            "name": staff.name,
            "role": staff.role,
        },
        business_id=current_user.business_id,
    )
    return staff


@router.get("/staff/{user_id}", response_model=UserOut)
async def get_staff(
    user_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await StaffService(db).get_user(user_id, current_user.business_id)


@router.patch("/staff/{user_id}", response_model=UserOut)
async def update_staff(
    user_id: str,
    data: StaffUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    staff = await StaffService(db).update_staff(current_user, user_id, data)
    await enqueue(
        db,
        Outbox,
        "staff.updated",
        {
            "userId": staff.id,
            "businessId": current_user.business_id,
            "name": staff.name,
            "role": staff.role,
        },
        business_id=current_user.business_id,
    )
    return staff

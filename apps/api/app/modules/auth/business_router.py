from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager, require_owner
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.modules.auth.business_schemas import BusinessOut, BusinessUpdate, LocationCreate, LocationOut
from app.modules.auth.business_service import BusinessService
from app.modules.staff.schemas import UserOut
from app.modules.staff.service import StaffService

router = APIRouter()


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await BusinessService(db).get_business(business_id)


@router.patch("/{business_id}", response_model=BusinessOut)
async def update_business(
    business_id: str,
    data: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    return await BusinessService(db).update_business(business_id, data)


@router.get("/{business_id}/locations", response_model=list[LocationOut])
async def list_locations(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await BusinessService(db).list_locations(business_id)


@router.post("/{business_id}/locations", response_model=LocationOut, status_code=201)
async def create_location(
    business_id: str,
    data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    return await BusinessService(db).create_location(business_id, data)


@router.get("/{business_id}/staff")
async def list_staff(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    users = await StaffService(db).list_staff(business_id)
    return [UserOut.model_validate(u) for u in users]

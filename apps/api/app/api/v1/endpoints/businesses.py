from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Business, Location, User
from app.schemas.business import BusinessOut, BusinessUpdate, LocationOut, LocationCreate
from app.api.v1.deps import get_current_user, require_owner, require_manager

router = APIRouter()


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.patch("/{business_id}", response_model=BusinessOut)
async def update_business(
    business_id: str,
    data: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(business, field, value)
    return business


@router.get("/{business_id}/locations", response_model=list[LocationOut])
async def list_locations(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Location).where(Location.business_id == business_id))
    return result.scalars().all()


@router.post("/{business_id}/locations", response_model=LocationOut, status_code=201)
async def create_location(
    business_id: str,
    data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_owner),
):
    location = Location(business_id=business_id, **data.model_dump())
    db.add(location)
    await db.flush()
    return location


@router.get("/{business_id}/staff")
async def list_staff(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    from app.services.staff import StaffService
    from app.schemas.staff import UserOut
    users = await StaffService(db).list_staff(business_id)
    return [UserOut.model_validate(u) for u in users]

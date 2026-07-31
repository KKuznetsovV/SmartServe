from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import Location, User
from app.db.session import get_db
from app.schemas.business import LocationOut, LocationUpdate

router = APIRouter()


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return loc


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: str,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(loc, field, value)
    return loc

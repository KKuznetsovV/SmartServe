from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.schemas.business import LocationOut, LocationUpdate
from app.services.business import BusinessService

router = APIRouter()


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await BusinessService(db).get_location(location_id)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: str,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await BusinessService(db).update_location(location_id, data)

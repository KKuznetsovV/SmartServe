from fastapi import Depends
from smartserve_shared.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_manager
from app.db.models import User
from app.db.session import get_db
from app.modules.auth.business_schemas import LocationOut, LocationUpdate
from app.modules.auth.business_service import BusinessService

router = APIRouter()


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BusinessService(db).get_location(location_id, current_user.business_id)


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: str,
    data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    return await BusinessService(db).update_location(location_id, data, current_user.business_id)

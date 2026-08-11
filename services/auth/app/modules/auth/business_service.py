"""Business and location CRUD logic shared by the businesses/locations endpoints."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, Location
from app.modules.auth.business_schemas import BusinessUpdate, LocationCreate, LocationUpdate


class BusinessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_business(self, business_id: str) -> Business:
        result = await self.db.execute(select(Business).where(Business.id == business_id))
        business = result.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
        return business

    async def update_business(self, business_id: str, data: BusinessUpdate) -> Business:
        business = await self.get_business(business_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(business, field, value)
        await self.db.flush()
        return business

    async def list_locations(self, business_id: str) -> list[Location]:
        result = await self.db.execute(select(Location).where(Location.business_id == business_id))
        return list(result.scalars().all())

    async def create_location(self, business_id: str, data: LocationCreate) -> Location:
        location = Location(business_id=business_id, **data.model_dump())
        self.db.add(location)
        await self.db.flush()
        return location

    async def get_location(self, location_id: str) -> Location:
        result = await self.db.execute(select(Location).where(Location.id == location_id))
        location = result.scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        return location

    async def update_location(self, location_id: str, data: LocationUpdate) -> Location:
        location = await self.get_location(location_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(location, field, value)
        await self.db.flush()
        return location

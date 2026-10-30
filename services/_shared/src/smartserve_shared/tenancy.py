"""Tenant ownership checks shared by every service that mirrors `locations`."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def verify_location_owned(
    db: AsyncSession,
    location_id: str,
    business_id: str,
    location_model: type[Any],
) -> Any:
    """Raise 404 unless `location_id` exists and belongs to `business_id`.

    Never trust a location id from a path or body alone. Other tenants always see 404,
    never 403, so existence of another business's location is not leaked.
    """
    result = await db.execute(
        select(location_model).where(location_model.id == location_id)
    )
    location = result.scalar_one_or_none()
    if not location or location.business_id != business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location not found"
        )
    return location

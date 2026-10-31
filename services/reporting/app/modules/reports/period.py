"""Resolve report query params into a UTC created_at range for a location."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from smartserve_shared.business_day import business_day_utc_range, period_date_range
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location


async def utc_range_for_location(
    db: AsyncSession,
    location_id: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    period: str | None = None,
    now: datetime | None = None,
) -> tuple[datetime, datetime, bool]:
    """Return (start, end, exclusive_end).

    Date params and `period` use the location timezone and cutoff. Legacy datetime
    `start`/`end` stay inclusive so existing clients keep working for one release.
    """
    location = await db.get(Location, location_id)
    tz_name = getattr(location, "timezone", None) if location is not None else None
    cutoff = getattr(location, "business_day_cutoff", None) if location is not None else None

    if start_date is not None or end_date is not None:
        if start_date is None or end_date is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date are required together",
            )
        low, high = business_day_utc_range(start_date, end_date, tz_name, cutoff)
        return low, high, True

    if start is not None and end is not None:
        return start, end, False

    if period:
        d0, d1 = period_date_range(period, now or datetime.now(UTC), tz_name, cutoff)
        low, high = business_day_utc_range(d0, d1, tz_name, cutoff)
        return low, high, True

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide start_date and end_date, or start and end, or period",
    )

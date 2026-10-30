"""Business-day cutoff for daily order numbers. Q9 will make the cutoff configurable."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_BUSINESS_DAY_CUTOFF = time(5, 0)


def business_date_for(
    now: datetime,
    timezone_name: str,
    cutoff: time = DEFAULT_BUSINESS_DAY_CUTOFF,
) -> date:
    """Calendar date of the business day that `now` belongs to at this location.

    Times before `cutoff` (currently 05:00 local) belong to the previous calendar day.
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local = now.astimezone(ZoneInfo(timezone_name))
    if local.time() < cutoff:
        return (local - timedelta(days=1)).date()
    return local.date()

"""Business-day cutoff shared by daily order numbers and reports."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo

DEFAULT_BUSINESS_DAY_CUTOFF = time(5, 0)
DEFAULT_TIMEZONE = "Asia/Jerusalem"

_RELATIVE_TODAY = frozenset({"today"})
_RELATIVE_YESTERDAY = frozenset({"yesterday"})
_RELATIVE_LAST_WEEK = frozenset({"last week", "last_week"})
_RELATIVE_THIS_WEEK = frozenset({"this week", "this_week"})
_RELATIVE_THIS_MONTH = frozenset({"this month", "this_month"})
_RELATIVE_LAST_MONTH = frozenset({"last month", "last_month"})


def parse_cutoff(value: time | str | None) -> time:
    if value is None or value == "":
        return DEFAULT_BUSINESS_DAY_CUTOFF
    if isinstance(value, time):
        return time(value.hour, value.minute, value.second)
    text = str(value).strip()
    if len(text) == 5:
        text = f"{text}:00"
    try:
        parsed = time.fromisoformat(text)
    except ValueError:
        return DEFAULT_BUSINESS_DAY_CUTOFF
    return time(parsed.hour, parsed.minute, parsed.second)


def _zone(timezone_name: str | None) -> tzinfo:
    name = timezone_name or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except Exception:
        return UTC


def business_date_for(
    now: datetime,
    timezone_name: str | None,
    cutoff: time | str | None = DEFAULT_BUSINESS_DAY_CUTOFF,
) -> date:
    """Calendar date of the business day that `now` belongs to at this location.

    Times before `cutoff` (default 05:00 local) belong to the previous calendar day.
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local = now.astimezone(_zone(timezone_name))
    edge = parse_cutoff(cutoff)
    if local.time() < edge:
        return (local - timedelta(days=1)).date()
    return local.date()


def business_day_utc_range(
    start_date: date,
    end_date: date,
    timezone_name: str | None,
    cutoff: time | str | None = DEFAULT_BUSINESS_DAY_CUTOFF,
) -> tuple[datetime, datetime]:
    """UTC half-open range covering business days `start_date` through `end_date` inclusive.

    start = start_date at cutoff local; end = (end_date + 1 day) at cutoff local.
    """
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    tz = _zone(timezone_name)
    edge = parse_cutoff(cutoff)
    start_local = datetime.combine(start_date, edge, tzinfo=tz)
    end_local = datetime.combine(end_date + timedelta(days=1), edge, tzinfo=tz)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def period_date_range(
    period: str,
    now: datetime,
    timezone_name: str | None,
    cutoff: time | str | None = DEFAULT_BUSINESS_DAY_CUTOFF,
) -> tuple[date, date]:
    today = business_date_for(now, timezone_name, cutoff)
    if period == "week":
        return today - timedelta(days=6), today
    if period == "month":
        return today - timedelta(days=29), today
    return today, today


def _month_bounds(day: date) -> tuple[date, date]:
    start = day.replace(day=1)
    if start.month == 12:
        next_month = date(start.year + 1, 1, 1)
    else:
        next_month = date(start.year, start.month + 1, 1)
    return start, next_month - timedelta(days=1)


def resolve_report_dates(
    start: str | None,
    end: str | None,
    *,
    now: datetime,
    timezone_name: str | None,
    cutoff: time | str | None = DEFAULT_BUSINESS_DAY_CUTOFF,
) -> tuple[date, date]:
    """Turn relative phrases or YYYY-MM-DD values into an inclusive business-date range."""
    today = business_date_for(now, timezone_name, cutoff)
    start_key = (start or "").strip().lower()
    end_key = (end or "").strip().lower()

    if start_key in _RELATIVE_THIS_MONTH or end_key in _RELATIVE_THIS_MONTH:
        return _month_bounds(today)
    if start_key in _RELATIVE_LAST_MONTH or end_key in _RELATIVE_LAST_MONTH:
        first, _ = _month_bounds(today)
        return _month_bounds(first - timedelta(days=1))
    if start_key in _RELATIVE_THIS_WEEK:
        monday = today - timedelta(days=today.weekday())
        return monday, today
    if start_key in _RELATIVE_LAST_WEEK:
        return today - timedelta(days=6), today

    def one(value: str, fallback: date) -> date:
        key = value.strip().lower()
        if not key:
            return fallback
        if key in _RELATIVE_TODAY:
            return today
        if key in _RELATIVE_YESTERDAY:
            return today - timedelta(days=1)
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError as exc:
            raise ValueError(f"Could not parse date '{value}'") from exc

    if not start or not end:
        raise ValueError("Could not determine the date range")
    return one(start, today), one(end, today)

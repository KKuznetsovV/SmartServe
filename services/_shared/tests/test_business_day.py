from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from smartserve_shared.business_day import (
    business_date_for,
    business_day_utc_range,
    period_date_range,
    resolve_report_dates,
)

TZ = "Asia/Jerusalem"


def test_before_cutoff_belongs_to_previous_calendar_day() -> None:
    now = datetime(2026, 10, 31, 2, 0, tzinfo=ZoneInfo(TZ))
    assert business_date_for(now, TZ) == date(2026, 10, 30)


def test_at_cutoff_starts_new_business_day() -> None:
    now = datetime(2026, 10, 31, 5, 0, tzinfo=ZoneInfo(TZ))
    assert business_date_for(now, TZ) == date(2026, 10, 31)


def test_sale_at_0130_tel_aviv_on_1_nov_counts_toward_31_oct() -> None:
    now = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo(TZ))
    assert business_date_for(now, TZ) == date(2026, 10, 31)


def test_today_at_0300_local_is_previous_business_day() -> None:
    now = datetime(2026, 11, 1, 3, 0, tzinfo=ZoneInfo(TZ))
    assert business_date_for(now, TZ) == date(2026, 10, 31)
    start, end = period_date_range("today", now, TZ)
    assert start == end == date(2026, 10, 31)


def test_dst_fallback_sunday_business_day_is_25_hours() -> None:
    # Israel DST ends 2026-10-25 02:00; business day 24 Oct runs Sat 05:00 IDT → Sun 05:00 IST.
    start, end = business_day_utc_range(date(2026, 10, 24), date(2026, 10, 24), TZ)
    assert end - start == timedelta(hours=25)


def test_resolve_today_and_last_week_use_business_date() -> None:
    now = datetime(2026, 11, 1, 3, 0, tzinfo=ZoneInfo(TZ))
    start, end = resolve_report_dates("today", "today", now=now, timezone_name=TZ)
    assert start == end == date(2026, 10, 31)
    week_start, week_end = resolve_report_dates("last week", "today", now=now, timezone_name=TZ)
    assert week_end == date(2026, 10, 31)
    assert week_start == date(2026, 10, 25)


def test_parse_cutoff_from_hhmm() -> None:
    start, end = business_day_utc_range(date(2026, 11, 1), date(2026, 11, 1), TZ, "04:00")
    local_start = start.astimezone(ZoneInfo(TZ))
    assert local_start.timetz().replace(tzinfo=None) == time(4, 0)
    assert end - start == timedelta(hours=24)

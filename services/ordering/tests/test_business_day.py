from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from smartserve_shared.business_day import business_date_for


def test_before_cutoff_belongs_to_previous_calendar_day() -> None:
    now = datetime(2026, 10, 31, 2, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
    assert business_date_for(now, "Asia/Jerusalem") == date(2026, 10, 30)


def test_at_cutoff_starts_new_business_day() -> None:
    now = datetime(2026, 10, 31, 5, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
    assert business_date_for(now, "Asia/Jerusalem") == date(2026, 10, 31)


def test_location_cutoff_is_honoured() -> None:
    now = datetime(2026, 10, 31, 4, 30, tzinfo=ZoneInfo("Asia/Jerusalem"))
    assert business_date_for(now, "Asia/Jerusalem", time(4, 0)) == date(2026, 10, 31)

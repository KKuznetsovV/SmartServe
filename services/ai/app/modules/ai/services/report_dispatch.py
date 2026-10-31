"""Resolves a classified `report.query` intent into a concrete reporting-service call.

This intent is read-only and deliberately bypasses the classify → /confirm → dispatch →
audit-publish flow every other (mutating) intent goes through — running a report never
changes any data, so there is nothing to confirm (see docs/microservices-plan.md §4c).
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from httpx import HTTPStatusError
from smartserve_shared.business_day import resolve_report_dates

from app.modules.ai.services.match import MatchError, match_index
from app.modules.ai.services.menu_client import MenuClient
from app.modules.ai.services.reports_client import ReportingClient

_VALID_REPORT_TYPES = {"sales", "sales_by_server", "closed_orders"}
_VALID_GROUP_BY = {"item", "category", "menu"}
_VALID_STATUS = {"paid", "cancelled", "other"}


def _report_dates(params: dict, location: dict | None, now: datetime | None) -> tuple[str, str]:
    loc = location or {}
    tz_name = loc.get("timezone")
    cutoff = loc.get("businessDayCutoff") or loc.get("business_day_cutoff")
    try:
        start, end = resolve_report_dates(
            params.get("start") or params.get("start_date"),
            params.get("end") or params.get("end_date"),
            now=now or datetime.now(UTC),
            timezone_name=tz_name,
            cutoff=cutoff,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return start.isoformat(), end.isoformat()


async def _resolve_item_and_category_hints(params: dict, location_id: str, token: str) -> tuple[str | None, str | None]:
    item_hint = params.get("item_hint")
    category_hint = params.get("category_hint")
    if not item_hint and not category_hint:
        return None, None

    menu = MenuClient(token)
    item_id = None
    category_id = None
    if item_hint:
        items = await menu.list_all_items(location_id)
        try:
            idx = match_index(item_hint, items)
        except MatchError:
            idx = None
        if idx is not None:
            item_id = items[idx]["id"]
    if category_hint:
        categories = await menu.list_categories(location_id)
        try:
            idx = match_index(category_hint, categories)
        except MatchError:
            idx = None
        if idx is not None:
            category_id = categories[idx]["id"]
    return item_id, category_id


async def generate_report(
    params: dict,
    location_id: str,
    token: str,
    *,
    location: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Resolve classified params (report_type/group_by/date range/item or category hint/
    status) into a reporting-service call and return its JSON result."""
    report_type = params.get("report_type")
    if report_type not in _VALID_REPORT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which report to run")

    start_date, end_date = _report_dates(params, location, now)
    reports = ReportingClient(token)

    try:
        if report_type == "sales":
            group_by_param = params.get("group_by")
            group_by = group_by_param if group_by_param in _VALID_GROUP_BY else "item"
            return await reports.sales(location_id, group_by=str(group_by), start_date=start_date, end_date=end_date)

        if report_type == "sales_by_server":
            item_id, category_id = await _resolve_item_and_category_hints(params, location_id, token)
            return await reports.sales_by_server(
                location_id, start_date=start_date, end_date=end_date, item_id=item_id, category_id=category_id
            )

        # closed_orders
        status_filter = params.get("status") if params.get("status") in _VALID_STATUS else None
        return await reports.closed_orders(
            location_id, start_date=start_date, end_date=end_date, status_filter=status_filter
        )
    except HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found") from exc
        if exc.response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report parameters") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="reporting service error") from exc

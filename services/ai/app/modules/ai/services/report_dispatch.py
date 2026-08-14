"""Resolves a classified `report.query` intent into a concrete reporting-service call.

This intent is read-only and deliberately bypasses the classify → /confirm → dispatch →
audit-publish flow every other (mutating) intent goes through — running a report never
changes any data, so there is nothing to confirm (see docs/microservices-plan.md §4c).
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from httpx import HTTPStatusError

from app.modules.ai.services.dispatch import fuzzy_match
from app.modules.ai.services.menu_client import MenuClient
from app.modules.ai.services.reports_client import ReportingClient

_VALID_REPORT_TYPES = {"sales", "sales_by_server", "closed_orders"}
_VALID_GROUP_BY = {"item", "category", "menu"}
_VALID_STATUS = {"paid", "cancelled", "other"}


def _parse_date(value: str | None, *, end_of_day: bool) -> str:
    """Parse a model-supplied YYYY-MM-DD (or full ISO) date into a UTC ISO datetime string,
    defaulting to start-of-day / end-of-day when only a bare date is given."""
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine the date range")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse date '{value}'") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if "T" not in value:
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    return parsed.isoformat()


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
        idx = fuzzy_match(item_hint, [i["name"] for i in items])
        if idx is not None:
            item_id = items[idx]["id"]
    if category_hint:
        categories = await menu.list_categories(location_id)
        idx = fuzzy_match(category_hint, [c["name"] for c in categories])
        if idx is not None:
            category_id = categories[idx]["id"]
    return item_id, category_id


async def generate_report(params: dict, location_id: str, token: str) -> dict:
    """Resolve classified params (report_type/group_by/date range/item or category hint/
    status) into a reporting-service call and return its JSON result."""
    report_type = params.get("report_type")
    if report_type not in _VALID_REPORT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine which report to run")

    start = _parse_date(params.get("start"), end_of_day=False)
    end = _parse_date(params.get("end"), end_of_day=True)
    reports = ReportingClient(token)

    try:
        if report_type == "sales":
            group_by_param = params.get("group_by")
            group_by = group_by_param if group_by_param in _VALID_GROUP_BY else "item"
            return await reports.sales(location_id, group_by=str(group_by), start=start, end=end)

        if report_type == "sales_by_server":
            item_id, category_id = await _resolve_item_and_category_hints(params, location_id, token)
            return await reports.sales_by_server(
                location_id, start=start, end=end, item_id=item_id, category_id=category_id
            )

        # closed_orders
        status_filter = params.get("status") if params.get("status") in _VALID_STATUS else None
        return await reports.closed_orders(location_id, start=start, end=end, status_filter=status_filter)
    except HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found") from exc
        if exc.response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report parameters") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="reporting service error") from exc

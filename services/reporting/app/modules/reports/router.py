from datetime import date, datetime
from typing import Literal

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from smartserve_shared.routing import APIRouter
from smartserve_shared.tenancy import verify_location_owned

from app.api.v1.deps import require_manager
from app.db.models import Location, User
from app.db.session import DbSession
from app.modules.reports.period import utc_range_for_location
from app.modules.reports.schemas import (
    ClosedOrdersReportOut,
    EventLogOut,
    ReportSummaryOut,
    SalesReportOut,
    ServerSalesReportOut,
)
from app.modules.reports.service import ReportService

router = APIRouter()


async def _range(
    db: DbSession,
    location_id: str,
    start_date: date | None,
    end_date: date | None,
    start: datetime | None,
    end: datetime | None,
    period: str | None = None,
) -> tuple[datetime, datetime, bool]:
    return await utc_range_for_location(
        db,
        location_id,
        start_date=start_date,
        end_date=end_date,
        start=start,
        end=end,
        period=period,
    )


@router.get("/locations/{location_id}/reports/summary", response_model=ReportSummaryOut)
async def get_report_summary(
    location_id: str,
    db: DbSession,
    period: Literal["today", "week", "month"] = "today",
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = Query(None, deprecated=True),
    end: datetime | None = Query(None, deprecated=True),
    current_user: User = Depends(require_manager),
) -> ReportSummaryOut:
    await verify_location_owned(db, location_id, current_user.business_id, Location)
    low, high, exclusive = await _range(db, location_id, start_date, end_date, start, end, period)
    return await ReportService(db).summary(location_id, period, low, high, exclusive)


@router.get("/locations/{location_id}/reports/sales", response_model=SalesReportOut)
async def get_sales_report(
    location_id: str,
    db: DbSession,
    group_by: Literal["item", "category", "menu"] = "item",
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = Query(None, deprecated=True),
    end: datetime | None = Query(None, deprecated=True),
    current_user: User = Depends(require_manager),
) -> SalesReportOut:
    await verify_location_owned(db, location_id, current_user.business_id, Location)
    low, high, exclusive = await _range(db, location_id, start_date, end_date, start, end)
    return await ReportService(db).sales_report(location_id, group_by, low, high, exclusive)


@router.get("/locations/{location_id}/reports/sales-by-server", response_model=ServerSalesReportOut)
async def get_sales_by_server_report(
    location_id: str,
    db: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = Query(None, deprecated=True),
    end: datetime | None = Query(None, deprecated=True),
    item_id: str | None = Query(None),
    category_id: str | None = Query(None),
    current_user: User = Depends(require_manager),
) -> ServerSalesReportOut:
    await verify_location_owned(db, location_id, current_user.business_id, Location)
    low, high, exclusive = await _range(db, location_id, start_date, end_date, start, end)
    return await ReportService(db).sales_by_server(location_id, low, high, item_id, category_id, exclusive)


@router.get("/locations/{location_id}/reports/closed-orders", response_model=ClosedOrdersReportOut)
async def get_closed_orders_report(
    location_id: str,
    db: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = Query(None, deprecated=True),
    end: datetime | None = Query(None, deprecated=True),
    status: Literal["paid", "cancelled", "other"] | None = Query(None),
    current_user: User = Depends(require_manager),
) -> ClosedOrdersReportOut:
    await verify_location_owned(db, location_id, current_user.business_id, Location)
    low, high, exclusive = await _range(db, location_id, start_date, end_date, start, end)
    return await ReportService(db).closed_orders(location_id, low, high, status, exclusive)


@router.get("/locations/{location_id}/reports/export")
async def export_report_csv(
    location_id: str,
    report_type: Literal["sales", "sales-by-server", "closed-orders"],
    db: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    start: datetime | None = Query(None, deprecated=True),
    end: datetime | None = Query(None, deprecated=True),
    group_by: Literal["item", "category", "menu"] = "item",
    item_id: str | None = Query(None),
    category_id: str | None = Query(None),
    status: Literal["paid", "cancelled", "other"] | None = Query(None),
    current_user: User = Depends(require_manager),
) -> StreamingResponse:
    await verify_location_owned(db, location_id, current_user.business_id, Location)
    low, high, exclusive = await _range(db, location_id, start_date, end_date, start, end)
    service = ReportService(db)

    if report_type == "sales":
        generator = service.stream_sales_csv(location_id, group_by, low, high, exclusive)
    elif report_type == "sales-by-server":
        generator = service.stream_sales_by_server_csv(location_id, low, high, item_id, category_id, exclusive)
    else:
        generator = service.stream_closed_orders_csv(location_id, low, high, status, exclusive)

    label_start = start_date or low.date()
    label_end = end_date or high.date()
    filename = f"{report_type}-{label_start}-to-{label_end}.csv"
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/events", response_model=list[EventLogOut])
async def list_events(
    db: DbSession,
    current_user: User = Depends(require_manager),
    routing_key: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    since: datetime | None = Query(None),
):
    return await ReportService(db).list_events(current_user.business_id, routing_key, limit, since)

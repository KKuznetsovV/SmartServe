from datetime import datetime
from typing import Literal

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.reports.schemas import (
    ClosedOrdersReportOut,
    EventLogOut,
    ReportSummaryOut,
    SalesReportOut,
    ServerSalesReportOut,
)
from app.modules.reports.service import ReportService, verify_location_owned

router = APIRouter()


@router.get("/locations/{location_id}/reports/summary", response_model=ReportSummaryOut)
async def get_report_summary(
    location_id: str,
    db: DbSession,
    period: Literal["today", "week", "month"] = "today",
    current_user: User = Depends(require_manager),
) -> ReportSummaryOut:
    await verify_location_owned(db, location_id, current_user.business_id)
    return await ReportService(db).summary(location_id, period)


@router.get("/locations/{location_id}/reports/sales", response_model=SalesReportOut)
async def get_sales_report(
    location_id: str,
    start: datetime,
    end: datetime,
    db: DbSession,
    group_by: Literal["item", "category", "menu"] = "item",
    current_user: User = Depends(require_manager),
) -> SalesReportOut:
    await verify_location_owned(db, location_id, current_user.business_id)
    return await ReportService(db).sales_report(location_id, group_by, start, end)


@router.get("/locations/{location_id}/reports/sales-by-server", response_model=ServerSalesReportOut)
async def get_sales_by_server_report(
    location_id: str,
    start: datetime,
    end: datetime,
    db: DbSession,
    item_id: str | None = Query(None),
    category_id: str | None = Query(None),
    current_user: User = Depends(require_manager),
) -> ServerSalesReportOut:
    await verify_location_owned(db, location_id, current_user.business_id)
    return await ReportService(db).sales_by_server(location_id, start, end, item_id, category_id)


@router.get("/locations/{location_id}/reports/closed-orders", response_model=ClosedOrdersReportOut)
async def get_closed_orders_report(
    location_id: str,
    start: datetime,
    end: datetime,
    db: DbSession,
    status: Literal["paid", "cancelled", "other"] | None = Query(None),
    current_user: User = Depends(require_manager),
) -> ClosedOrdersReportOut:
    await verify_location_owned(db, location_id, current_user.business_id)
    return await ReportService(db).closed_orders(location_id, start, end, status)


@router.get("/locations/{location_id}/reports/export")
async def export_report_csv(
    location_id: str,
    report_type: Literal["sales", "sales-by-server", "closed-orders"],
    start: datetime,
    end: datetime,
    db: DbSession,
    group_by: Literal["item", "category", "menu"] = "item",
    item_id: str | None = Query(None),
    category_id: str | None = Query(None),
    status: Literal["paid", "cancelled", "other"] | None = Query(None),
    current_user: User = Depends(require_manager),
) -> StreamingResponse:
    await verify_location_owned(db, location_id, current_user.business_id)
    service = ReportService(db)

    if report_type == "sales":
        generator = service.stream_sales_csv(location_id, group_by, start, end)
    elif report_type == "sales-by-server":
        generator = service.stream_sales_by_server_csv(location_id, start, end, item_id, category_id)
    else:
        generator = service.stream_closed_orders_csv(location_id, start, end, status)

    filename = f"{report_type}-{start.date()}-to-{end.date()}.csv"
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/events", response_model=list[EventLogOut])
async def list_events(
    db: DbSession,
    routing_key: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(require_manager),
):
    return await ReportService(db).list_events(routing_key, limit)

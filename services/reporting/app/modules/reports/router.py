from typing import Literal

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.modules.reports.schemas import EventLogOut, ReportSummaryOut
from app.modules.reports.service import ReportService

router = APIRouter()


@router.get("/locations/{location_id}/reports/summary", response_model=ReportSummaryOut)
async def get_report_summary(
    location_id: str,
    period: Literal["today", "week", "month"] = "today",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
) -> ReportSummaryOut:
    return await ReportService(db).summary(location_id, period)


@router.get("/events", response_model=list[EventLogOut])
async def list_events(
    routing_key: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await ReportService(db).list_events(routing_key, limit)

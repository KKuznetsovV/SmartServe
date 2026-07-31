from typing import Literal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router_base import APIRouter
from app.db.session import get_db
from app.schemas.report import ReportSummaryOut
from app.services.report import ReportService

router = APIRouter()


@router.get("/locations/{location_id}/reports/summary", response_model=ReportSummaryOut)
async def get_report_summary(
    location_id: str,
    period: Literal["today", "week", "month"] = "today",
    db: AsyncSession = Depends(get_db),
) -> ReportSummaryOut:
    return await ReportService(db).summary(location_id, period)

from smartserve_shared.routing import APIRouter

from app.modules.reports.router import router as reports

api_router = APIRouter()

api_router.include_router(reports, tags=["reports"])

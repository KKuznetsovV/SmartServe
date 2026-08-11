from app.api.v1.router_base import APIRouter
from app.modules.reports.router import router as reports

api_router = APIRouter()

api_router.include_router(reports, tags=["reports"])

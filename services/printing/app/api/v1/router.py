from smartserve_shared.routing import APIRouter

from app.modules.printing.router import router as printing

api_router = APIRouter()

api_router.include_router(printing, tags=["printing"])

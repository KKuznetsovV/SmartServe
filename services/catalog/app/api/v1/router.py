from app.api.v1.router_base import APIRouter
from app.modules.catalog.discount_router import router as discounts
from app.modules.catalog.router import router as menu

api_router = APIRouter()

api_router.include_router(menu, prefix="/menu", tags=["menu"])
api_router.include_router(discounts, tags=["discounts"])

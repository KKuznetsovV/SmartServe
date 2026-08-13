from app.api.v1.router_base import APIRouter
from app.modules.ai.router import router as ai

api_router = APIRouter()

api_router.include_router(ai, prefix="/ai", tags=["ai"])

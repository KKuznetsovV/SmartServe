from app.api.v1.router_base import APIRouter
from app.modules.payments.router import router as payments

api_router = APIRouter()

api_router.include_router(payments, tags=["payments"])

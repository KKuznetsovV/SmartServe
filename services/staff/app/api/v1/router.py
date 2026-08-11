from app.api.v1.router_base import APIRouter
from app.modules.staff.router import router as staff
from app.modules.staff.shift_router import router as shifts

api_router = APIRouter()

api_router.include_router(staff, tags=["staff"])
api_router.include_router(shifts, tags=["shifts"])

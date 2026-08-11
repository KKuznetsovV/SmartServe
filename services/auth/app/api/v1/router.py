from app.api.v1.router_base import APIRouter
from app.modules.auth.business_router import router as businesses
from app.modules.auth.location_router import router as locations
from app.modules.auth.router import router as auth

api_router = APIRouter()

api_router.include_router(auth, prefix="/auth", tags=["auth"])
api_router.include_router(businesses, prefix="/businesses", tags=["businesses"])
api_router.include_router(locations, prefix="/locations", tags=["locations"])

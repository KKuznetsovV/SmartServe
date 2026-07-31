from app.api.v1.router_base import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "smartserve-api"}

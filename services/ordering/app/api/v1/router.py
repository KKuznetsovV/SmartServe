from app.api.v1.router_base import APIRouter
from app.modules.ordering.router import router as orders
from app.modules.ordering.table_router import router as tables
from app.modules.ordering.ws_router import router as ws

api_router = APIRouter()

# Tables endpoint handles both /locations/{id}/tables and /tables routes
api_router.include_router(tables, tags=["tables"])
# Orders endpoint handles /locations/{id}/orders and /orders/* routes
api_router.include_router(orders, tags=["orders"])
# Real-time order/KDS events — migrated from apps/api in Step 25
api_router.include_router(ws, prefix="/ws", tags=["websocket"])

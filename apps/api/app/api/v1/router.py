from fastapi import APIRouter

from app.api.v1.endpoints import auth, businesses, locations, menu, tables, orders, payments, printers, staff, ai, ws, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
api_router.include_router(tables.router, prefix="/tables", tags=["tables"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(printers.router, prefix="/printers", tags=["printers"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

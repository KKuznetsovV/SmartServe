from app.api.v1.endpoints import (
    ai,
    auth,
    businesses,
    health,
    locations,
    menu,
    orders,
    payments,
    printers,
    reports,
    staff,
    tables,
    ws,
)
from app.api.v1.router_base import APIRouter

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
# Menu routes span categories, items, modifiers — no prefix so internal paths are clean
api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
# Tables endpoint handles both /locations/{id}/tables and /tables routes
api_router.include_router(tables.router, tags=["tables"])
# Orders endpoint handles /locations/{id}/orders and /orders/* routes
api_router.include_router(orders.router, tags=["orders"])
# Payments and printer-routes have order-scoped and standalone paths
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(printers.router, tags=["printers"])
api_router.include_router(staff.router, tags=["staff"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

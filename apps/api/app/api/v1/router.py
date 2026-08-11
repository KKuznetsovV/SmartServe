from app.api.v1.endpoints import health, ws
from app.api.v1.router_base import APIRouter
from app.modules.ai.router import router as ai
from app.modules.catalog.discount_router import router as discounts
from app.modules.catalog.router import router as menu
from app.modules.ordering.router import router as orders
from app.modules.ordering.table_router import router as tables
from app.modules.payments.router import router as payments
from app.modules.printing.router import router as printers
from app.modules.reports.router import router as reports
from app.modules.staff.router import router as staff
from app.modules.staff.shift_router import router as shifts

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# auth, businesses, locations moved to services/auth (Step 17) — gateway routes those
# path prefixes there directly; the gateway no longer forwards them to this monolith.
# Menu routes span categories, items, modifiers — no prefix so internal paths are clean
api_router.include_router(menu, prefix="/menu", tags=["menu"])
# Tables endpoint handles both /locations/{id}/tables and /tables routes
api_router.include_router(tables, tags=["tables"])
# Orders endpoint handles /locations/{id}/orders and /orders/* routes
api_router.include_router(orders, tags=["orders"])
# Payments and printer-routes have order-scoped and standalone paths
api_router.include_router(payments, tags=["payments"])
api_router.include_router(printers, tags=["printers"])
api_router.include_router(staff, tags=["staff"])
api_router.include_router(reports, tags=["reports"])
api_router.include_router(discounts, tags=["discounts"])
api_router.include_router(shifts, tags=["shifts"])
api_router.include_router(ai, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

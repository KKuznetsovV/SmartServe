from app.api.v1.endpoints import health, ws
from app.api.v1.router_base import APIRouter
from app.modules.ai.router import router as ai
from app.modules.printing.router import router as printers
from app.modules.reports.router import router as reports
from app.modules.staff.router import router as staff
from app.modules.staff.shift_router import router as shifts

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# auth, businesses, locations moved to services/auth (Step 17) — gateway routes those
# path prefixes there directly; the gateway no longer forwards them to this monolith.
# menu, discounts moved to services/catalog (Step 18) — apps/api keeps a local copy of
# MenuService (app/modules/catalog/service.py) only for in-process use by the ai module,
# it is no longer exposed over HTTP here.
# orders, tables moved to services/ordering (Step 19); payments moved to services/payments
# (Step 20) — printing/reports keep reading/writing the shared Order/OrderItem/Table
# tables directly (same DB) since their own extraction hasn't happened yet; see
# docs/microservices-plan.md §4.
api_router.include_router(printers, tags=["printers"])
api_router.include_router(staff, tags=["staff"])
api_router.include_router(reports, tags=["reports"])
api_router.include_router(shifts, tags=["shifts"])
api_router.include_router(ai, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

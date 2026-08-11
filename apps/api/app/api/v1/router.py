from app.api.v1.endpoints import health, ws
from app.api.v1.router_base import APIRouter
from app.modules.ai.router import router as ai
from app.modules.reports.router import router as reports

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# auth, businesses, locations moved to services/auth (Step 17) — gateway routes those
# path prefixes there directly; the gateway no longer forwards them to this monolith.
# menu, discounts moved to services/catalog (Step 18) — apps/api keeps a local copy of
# MenuService (app/modules/catalog/service.py) only for in-process use by the ai module,
# it is no longer exposed over HTTP here.
# orders, tables moved to services/ordering (Step 19); payments moved to services/payments
# (Step 20); staff/shifts moved to services/staff (Step 21); printing moved to
# services/printing (Step 22) — apps/api keeps the Printer/PrinterRoute ORM models
# (app/db/models.py) only for in-process read access by the ai module's menu-import
# printer-type suggestions, they are no longer exposed over HTTP here. reports keeps
# reading the shared Order/OrderItem/Table tables directly (same DB) since its own
# extraction hasn't happened yet; see docs/microservices-plan.md §4.
api_router.include_router(reports, tags=["reports"])
api_router.include_router(ai, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

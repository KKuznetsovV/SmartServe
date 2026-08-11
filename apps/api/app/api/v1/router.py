from app.api.v1.endpoints import health, ws
from app.api.v1.router_base import APIRouter
from app.modules.ai.router import router as ai

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# auth, businesses, locations moved to services/auth (Step 17) — gateway routes those
# path prefixes there directly; the gateway no longer forwards them to this monolith.
# menu, discounts moved to services/catalog (Step 18) — apps/api keeps a local copy of
# MenuService (app/modules/catalog/service.py) only for in-process use by the ai module,
# it is no longer exposed over HTTP here.
# orders, tables moved to services/ordering (Step 19); payments moved to services/payments
# (Step 20); staff/shifts moved to services/staff (Step 21); printing moved to
# services/printing (Step 22); reports moved to services/reporting (Step 23) — apps/api
# keeps the Printer/PrinterRoute ORM models (app/db/models.py) only for in-process read
# access by the ai module's menu-import printer-type suggestions, they are no longer
# exposed over HTTP here. Order/OrderItem were removed entirely (only reports/payments
# read them in-process, and both have now been extracted); see
# docs/microservices-plan.md §4.
api_router.include_router(ai, prefix="/ai", tags=["ai"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

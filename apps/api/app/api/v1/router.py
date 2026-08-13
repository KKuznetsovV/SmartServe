from app.api.v1.endpoints import health, ws
from app.api.v1.router_base import APIRouter

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# auth, businesses, locations moved to services/auth (Step 17); menu, discounts moved to
# services/catalog (Step 18); orders, tables moved to services/ordering (Step 19);
# payments moved to services/payments (Step 20); staff/shifts moved to services/staff
# (Step 21); printing moved to services/printing (Step 22); reports moved to
# services/reporting (Step 23); ai moved to services/ai (Step 24) — apps/api's
# app/modules/catalog (in-process MenuService) and the Printer/PrinterRoute ORM models
# were only kept around for the ai module's in-process use and have now been fully
# removed along with it. Order/OrderItem were removed in Step 23. The only remaining
# in-process modules are health/ws below; see docs/microservices-plan.md §4 — apps/api
# itself is slated for full retirement in Step 25.
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])

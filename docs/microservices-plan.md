# SmartServe — Folder Structure & Microservices Scalability Plan

> Proposed: 2026-08-11 · Approved scope: full domain decomposition (see §4)
> Companion to [architecture.md](./architecture.md). This document is the working plan for (1) tidying the
> monorepo layout and (2) splitting the `apps/api` monolith into independently deployable domain services.

---

## 1. Current-state assessment

- **Frontends**: `apps/web` (admin dashboard), `apps/orders` (staff order UI), `apps/pos` (Expo tablet app,
  currently a skeleton — one `index.tsx`). `web` and `orders` are two separate Next.js apps that each vendor
  their own copy of the same shadcn/ui primitives (`Button`, `Dialog`, `Input`, `Card`, `Badge`, ...) and their
  own `eslint.config.mjs`/`tsconfig.json` boilerplate — real duplication, no shared UI or config package exists
  yet despite `packages/ui` being referenced in `architecture.md` §3.4.
- **Backend**: a single FastAPI app (`apps/api`) organized *by technical layer* (`api/v1/endpoints/*.py` routers,
  `schemas/*.py`, `services/*.py`) rather than *by domain* — all 15 SQLAlchemy models live in one
  `db/models.py`. One Postgres database, one Redis instance, one Dockerfile.

**Noted trade-off (for the record)**: at the current scale (single developer, single Postgres instance) a full
microservices split trades a small well-tested monolith for distributed-transaction/eventual-consistency
complexity. The plan below manages that cost pragmatically — same Postgres *instance*, one schema per service
(so no new infra to run), cross-service reads go through the owning service's REST API or small denormalized
projections, and writes that need to fan out use Redis pub/sub events rather than distributed transactions.

---

## 2. Optimized monorepo folder tree

```
SmartServe/
├── apps/                      # user-facing frontends only
│   ├── web/                   # Next.js admin dashboard (unchanged)
│   ├── orders/                 # Next.js staff order UI (unchanged)
│   └── pos/                    # Expo tablet app (unchanged)
├── services/                   # NEW — every backend domain service lives here
│   ├── gateway/                 # reverse-proxy / routing layer (single base URL for all frontends)
│   ├── auth/                    # businesses, locations, users, JWT issuance/refresh, PIN login
│   ├── catalog/                 # menu categories/items/modifiers, discounts
│   ├── ordering/                # tables, orders, order_items — publishes order/item events
│   ├── payments/                # payments, tip/split, gateway abstraction
│   ├── staff/                   # staff shifts, clock-in/out
│   ├── printing/                # printer routing + KDS event fan-out
│   ├── reporting/                # read-only analytics, fed by events
│   ├── ai/                       # AI intent classification/execution orchestration
│   └── _shared/                  # small internal-only Python lib: JWT verify, service HTTP client, event helpers
├── packages/                    # frontend-only shared code
│   ├── types/                    # unchanged — shared TS types/Zod schemas
│   ├── api-client/                # unchanged — typed fetch client (still points at the gateway's base URL)
│   ├── ui/                       # NEW — shared shadcn/ui primitives used by web + orders
│   └── config/                   # NEW — shared eslint-config / tsconfig / tailwind-config
├── docs/
│   ├── architecture.md
│   └── microservices-plan.md      # this file
├── .github/workflows/ci.yml        # one job per service
├── docker-compose.yml               # one entry per service + gateway
└── ...
```

`apps/api` is retired once all of its modules have been migrated into `services/*` (§6, final step). `apps/`
now means "things end users load in a browser/tablet"; `services/` means "backend processes."

---

## 3. `services/_shared` — the only intentionally shared backend code

To avoid standing up a package registry for one internal library, `_shared` is imported by path (editable
pip install, `-e ../_shared`) by every service's `requirements.txt`. It contains only:
- `security.py` — JWT verification (decode + validate `exp`/`sub`/`business_id`/`location_id` claims). Every
  service verifies the same token locally; there is no per-request call to `auth`.
- `http_client.py` — a thin `httpx.AsyncClient` wrapper for service-to-service REST calls (base URL from env,
  forwards the caller's JWT for downstream authorization).
- `events.py` — Redis pub/sub publish/subscribe helpers with a shared event-name/payload convention.

This is deliberately small — no service mesh, no circuit breakers, no distributed tracing. Add those later
only if real operational pain shows up.

---

## 4. Service boundaries (final, approved)

| Service | Owns (DB schema) | Depends on (sync REST) | Publishes / subscribes (async, Redis) |
|---|---|---|---|
| `gateway` | none (stateless reverse proxy) | routes to all services | — |
| `auth` | `auth.businesses`, `auth.locations`, `auth.users` | — | — |
| `catalog` | `catalog.menu_categories`, `catalog.menu_items`, `catalog.modifier_groups`, `catalog.modifiers`, `catalog.discounts` | `auth` (validate location) | publishes `catalog.item_updated` |
| `ordering` | `ordering.tables`, `ordering.orders`, `ordering.order_items` | `auth` (validate location/user), `catalog` (fetch item price/name at order time) | publishes `order.updated`, `order.item_fired`; subscribes `payment.completed` (mark order paid) |
| `payments` | `payments.payments` | `auth`, `ordering` (fetch order total/remaining) | publishes `payment.completed` |
| `staff` | `staff.shifts` | `auth` (validate user) | — |
| `printing` | `printing.printers`, `printing.printer_routes` | `auth`, `catalog` (item→printer routing rules) | subscribes `order.item_fired` |
| `reporting` | `reporting.*` (denormalized projections only) | — | subscribes `order.updated`, `payment.completed`, `catalog.item_updated` |
| `ai` | none (stateless orchestrator) | calls whichever service is needed to execute a confirmed action | — |

Cross-service references (e.g. `ordering.orders.location_id` pointing at a row `auth` owns) are stored as
plain UUID columns, not enforced foreign keys — each service enforces its own referential integrity; a
cross-service reference is validated via that service's REST API at write time, not at the DB level.

---

## 5. Gateway & frontend compatibility

`services/gateway` is an nginx container that keeps `NEXT_PUBLIC_API_URL`/`packages/api-client` pointed at
one stable base URL and routes by path prefix to the right service container over the Docker network:

```
/auth/*, /businesses/*, /locations/*   → auth:8000
/menu/*, /discounts/*                  → catalog:8000
/orders/*, /tables/*, /ws/*            → ordering:8000
/payments/*                            → payments:8000
/staff/*, /shifts/*                    → staff:8000
/printers/*                            → printing:8000
/reports/*                             → reporting:8000
/ai/*                                  → ai:8000
```

This means **no frontend code changes** are required as services get extracted one at a time — only the
gateway config and docker-compose gain a new route/entry per step.

---

## 6. Step-by-step execution plan (each step = its own branch, build-checked, merged, pushed)

| Step | Branch | Scope | Build check |
|---|---|---|---|
| 14 | `refactor/shared-ui-and-config-packages` | Extract `packages/ui` + `packages/config`; repoint `apps/web`/`apps/orders` | `pnpm turbo run build lint typecheck` |
| 15 | `refactor/api-modular-monolith` | Reorganize `apps/api/app` into `modules/{auth,catalog,ordering,payments,staff,printing,reports,ai}`, no behavior change | ruff/mypy/pytest (38/38) |
| 16 | `platform/gateway-and-shared-lib` | Add `services/gateway` (nginx) + `services/_shared`; gateway routes 100% to existing `apps/api` (no behavior change yet); docker-compose updated so frontends hit the gateway | `docker build` gateway + full compose smoke test |
| 17 | `service/auth-extraction` | Extract `auth` module → `services/auth` (own Dockerfile, own Alembic chain, own `auth` schema); gateway routes `/auth/*`,`/businesses/*`,`/locations/*` to it | new service ruff/mypy/pytest + `docker build` + gateway smoke test |
| 18 | `service/catalog-extraction` | Extract `catalog` module → `services/catalog`, calls `auth` for location validation | same pattern |
| 19 | `service/ordering-extraction` | Extract `ordering` module → `services/ordering`, calls `catalog`/`auth`, publishes order/item events | same pattern + regression test for split/quantity-action logic |
| 20 | `service/payments-extraction` | Extract `payments` module → `services/payments`, calls `ordering`, publishes `payment.completed` | same pattern + regression test for split/tip/cumulative-paid logic |
| 21 | `service/staff-extraction` | Extract `staff` module → `services/staff` | same pattern |
| 22 | `service/printing-extraction` | Extract `printing` module → `services/printing`, subscribes to `order.item_fired` | same pattern |
| 23 | `service/reporting-extraction` | Extract `reporting` module → `services/reporting`, builds projections from subscribed events | same pattern |
| 24 | `service/ai-extraction` | Extract `ai` module → `services/ai`, calls other services via `_shared/http_client.py` | same pattern |
| 25 | `chore/retire-api-monolith` | Remove `apps/api` once all modules are migrated and gateway fully routes to the new services | full docker-compose smoke test (all services up, health checks green) |

Each step: new branch → implement → validate → commit → `git checkout main && git merge --no-ff` →
`git push origin main` → delete local feature branch, exactly as done for prior features in this repo.

# SmartServe — Folder Structure & Microservices Scalability Plan

> Proposed: 2026-08-11 · Approved scope: full domain decomposition (see §4)
> Companion to [architecture.md](./architecture.md). This document is the working plan for (1) tidying the
> monorepo layout and (2) splitting the `apps/api` monolith into independently deployable domain services.
>
> **Status: complete.** All 25 steps in §6 have been executed — every domain now lives in its own
> `services/*` FastAPI app behind `services/gateway`, and `apps/api` has been removed from the repo. This
> document is kept as a historical record of the plan and rationale.

---

## Step 28 (post-migration): Menu item trash / soft-delete

`MenuService.delete_item()` previously did a permanent `db.delete(item)` — no soft-delete state existed
anywhere, so removing a menu item was irreversible and (worse) any historical `OrderItem`/reporting record
still logically pointing at that item's id had no real row to ever look back at. Step 28 replaces this with
a proper trash state: move-to-trash, restore, and an explicit, separate permanent-delete.

- **`catalog`**: `MenuItem` gained a `deleted_at: datetime | None` timestamp column (Alembic migration
  `0002_menu_item_trash`, on top of a brand-new baseline Alembic chain for this service — `services/catalog`
  had no Alembic setup at all before this pass, unlike `ordering`/`reporting`). Deliberately a separate
  column from `active`/`in_stock` (which drive the existing toggle-availability feature) rather than reusing
  either of them. `delete_item()` now sets `deleted_at` instead of deleting the row; a new `restore_item()`
  clears it (400s if the item isn't actually trashed); a new `permanently_delete_item()` performs the real
  `db.delete()` and only succeeds on an already-trashed item (400s otherwise) — permanent delete is always a
  second, explicit step, never implicit in the regular delete endpoint.
- **Trashed items excluded from every default listing**: `list_items`, `list_all_items`, and
  `bulk_price_update` all now filter `deleted_at IS NULL`. This covers every consumer that reads through
  those catalog endpoints — the menu editor, `apps/orders`' order-taking grid, printer routing, and the AI
  dispatch layer's item lookups — without needing changes in any of those services, since catalog is the
  single source of truth for the active item set. A new `GET /locations/{location_id}/trash` endpoint
  (manager-only) is the only way to see trashed items.
- **Historical data is unaffected**: `ordering`'s own `OrderItem` rows snapshot `menu_item_name`/`unit_price`
  at the time the item was added and never join live to `MenuItem` for display; `reporting`'s `OrderItem`
  mirror has its own independent `menu_item_name`/`category_name` snapshot columns and never joins to a live
  `MenuItem` either. Verified directly (not assumed) by tracing every `MenuItem` query site in both services,
  and covered by a new ordering test that trashes, then permanently deletes, the underlying `MenuItem` after
  it's already on an order and asserts the order's display is unchanged. The one live lookup that *does* now
  filter on `deleted_at` is `ordering.add_item()` — validating a **new** item being added to an order — so a
  trashed item can't be added going forward, while anything already on an existing order keeps resolving
  regardless of trash state.
- **AI intents**: `menu.move_to_trash`, `menu.restore_item`, and `menu.permanently_delete_item` were added to
  `SUPPORTED_INTENTS` with few-shot examples in `INTENT_SYSTEM_PROMPT`. Restore/permanent-delete resolve
  their target from the trash list (`MenuClient.list_trashed_items`), not the active-item list `_resolve_item`
  normally searches, via a new `_resolve_trashed_item` helper. `permanently_delete_item` requires confirmation
  like every other mutating intent — `ai_command` already sets `requiresConfirmation: True` for every intent
  except the read-only `report.query`, so no extra code was needed for that guarantee.
- **Frontend**: the menu editor's existing delete button needed no code change — it already calls
  `DELETE /items/{id}`, which now soft-deletes server-side. Added a "View Trash" dialog
  (`apps/web/src/components/menu/trash-dialog.tsx`) listing trashed items per location with Restore and
  Permanently Delete (with an inline confirm step, since it's irreversible) actions.
- **Scope note**: automatic purge of trashed items after a retention window (e.g. 6 months) is explicitly
  deferred to a future feature — it needs job-scheduling infrastructure this codebase doesn't have yet
  (nothing currently runs on a schedule; every existing "background" action is either request-triggered or an
  event-bus consumer). Manual permanent-delete (above) is the only purge path this pass implements.

---

## Step 27 (post-migration): AI chat assistant hardening

Step 26 wired `ai`'s `POST /ai/command` → `POST /ai/confirm` flow and the `ai.action_executed` event, but a
few gaps remained between that first cut and the actual "manager types a request, the system carries it out"
requirement. Step 27 closes them without introducing any new services.

- **JWT-scoped location validation moved earlier**: `ai_confirm` already verified the target `locationId`
  belongs to the caller's own (JWT-verified) `business_id` before executing. `ai_command` (classify step) now
  runs the same `_get_owned_location` check *before* calling Anthropic, so a caller can't even get a preview
  generated against another business's location, and a missing/foreign `locationId` fails fast with 400/404
  instead of silently classifying against nothing.
- **`printer.route` intent implemented**: `dispatch.py` gained `_dispatch_printer_route()`, resolving the
  target printer by fuzzy name-then-type match (`services/printing`) and the target items either by
  `category_hint` (bulk, e.g. "all bar tickets") or `item_hints`/`item_hint` (specific items) via
  `services/catalog`. Defaults to replacing conflicting existing routes (`replace_existing`, matching
  "route X to Y **instead**" phrasing); pass `add_only: true` in params to add without removing.
- **Audit log enriched**: the `ai.action_executed` payload (consumed by `reporting`'s `EventLog`) now includes
  `businessId`, `userId` (`ctx.claims.sub`), and `originalMessage`, not just `intent`/`params`/`locationId`, so
  the audit trail actually answers "who asked for what, in their own words."
- **Real-time propagation for AI-driven catalog changes**: `catalog` now includes `locationId` in every
  `catalog.item_updated` payload (previously only its bulk-price-change endpoint did). `ordering` — the sole
  service the gateway proxies WebSocket traffic to — gained a second RabbitMQ consumer
  (`ordering.realtime_relay`, binding `catalog.item_updated`) that relays the event to connected clients via
  its existing `ws_router.broadcast()`, as a new `menu.item_updated` WS message. This was chosen over adding a
  WS runtime to `services/gateway` (pure nginx, no app process) or building new infrastructure, reusing the
  one WS connection every dashboard screen already holds open. `apps/web`'s `useLocationWs` hook was lifted
  from the Dashboard page into the shared `(dashboard)/layout.tsx` (so it's connected regardless of which
  screen is open) and now invalidates `['items']`/`['categories', locationId]` on `menu.item_updated`.
- **Frontend**: extracted the AI chat's proposed-action card into `AiConfirmationCard`
  (`apps/web/src/app/(dashboard)/ai/confirmation-card.tsx`) built from the existing local `@/components/ui/*`
  wrappers (`@smartserve/ui` re-exports); message/preview bubbles use `dir="auto"` so Hebrew and English text
  render correctly regardless of the dashboard's overall locale direction.
- **Scope note**: per-user location authorization (JWT carrying a `location_ids` array, rather than
  business-wide access) was explicitly deferred to a future feature — this pass keeps the existing
  business-wide (`business_id`-only) authorization model.

---

## Step 26 (post-migration): RabbitMQ event bus

The original plan (§1) called for cross-service fan-out via Redis pub/sub, but that was never actually
implemented — `services/_shared/events.py` was a dead scaffold with no callers. Step 26 replaces that
intention with a real durable event bus using **RabbitMQ** (topic exchange `smartserve.events`, dotted
routing keys), scoped broadly as general audit/eventing infrastructure rather than just order/payment flows.

- **Publishers**: `catalog` (`catalog.item_updated`), `ordering` (`order.created`, `order.updated`,
  `order.item_fired`), `payments` (`payment.completed`, only on full payment), `staff` (`staff.created`,
  `staff.updated`), `ai` (`ai.action_executed`, after a confirmed AI command executes).
- **Consumers**: `ordering` consumes `payment.completed` to transition its local order to `paid` (idempotent);
  `printing` consumes `order.item_fired` to create `PrintJob` audit rows for each matching `PrinterRoute`
  (exposed via `GET /locations/{id}/print-jobs`); `reporting` consumes every event via a wildcard (`#`) binding
  into a new `EventLog` table (generic audit trail, `GET /events`) and additionally projects `order.created`/
  `order.updated`/`payment.completed` into its own `Order` mirror — this also fixes a real pre-existing bug
  where reporting's Order/OrderItem mirror was never populated by anything, so `/reports/summary` always
  returned zero rows.
- **Implementation**: each of the 7 participating services gets its own `app/core/mq.py` (same duplication
  convention as the rest of the codebase, not a `_shared` module) with `connect`/`publish`/`consume_forever`
  helpers built on `aio-pika`. `publish` and `connect` never raise — a broker outage degrades to "no events
  published" rather than breaking the request path. `app.state.mq_connection = None` is set in `create_app()`
  before `lifespan` runs, since `httpx.ASGITransport` doesn't trigger `lifespan` during tests, keeping
  `mq.publish(None, ...)` a safe no-op in the test suite.
- **Incidental fix**: while wiring `ai`, a pre-existing Python 2-style `except json.JSONDecodeError, IndexError,
  KeyError:` clause (invalid Python 3 syntax) was discovered and corrected in `services/ai/app/modules/ai/router.py`.
- `docker-compose.yml` gained a `rabbitmq` service (management image + healthcheck), consumed via `RABBITMQ_URL`
  by all 7 participating services.

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

**Note on Step 15**: `db/models.py`'s 15 ORM models are deeply cross-referenced (e.g. `Order` touches
`Location`, `Table`, `Discount`, `Payment`, `MenuItem`). Splitting that file per-module at this step would
require SQLAlchemy forward-ref workarounds for a purely organizational win, since everything still runs as
one monolith. Step 15 reorganizes the router/schema/service layers into `modules/*` and leaves `db/models.py`
as a single cross-cutting file; each Tier-1 extraction step (17-24) does its own trimmed-down model split
for just the tables that service owns, with cross-service references as plain UUID columns (per §4) — that's
where the split actually pays off.

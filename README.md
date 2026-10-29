# SmartServe

SmartServe is a next-generation restaurant and commercial POS system targeting the Israeli market. Its core
differentiator is an **AI-powered management backend** that lets non-technical restaurant managers configure
menus, prices, printer routing, and staff through natural language instead of complex admin screens.

Full product/design rationale lives in [docs/architecture.md](docs/architecture.md). The backend's ongoing
migration from a monolith to microservices is tracked in [docs/microservices-plan.md](docs/microservices-plan.md).

## Key principles

- **AI efficiency first** — Claude Haiku for cheap intent classification, Claude Sonnet only for complex reasoning.
- **Offline resilience** — the tablet POS works offline and syncs when reconnected.
- **RTL-native** — Hebrew is a first-class language across every UI.
- **Multi-tenant from day one** — every entity is scoped to a `business_id` + `location_id`.
- **Real-time everywhere** — order/KDS/stock updates propagate via WebSockets.

## Monorepo structure

```
SmartServe/
├── apps/                    # user-facing frontends
│   ├── web/                  # Next.js 14 admin dashboard
│   ├── orders/                # Next.js staff order UI
│   └── pos/                    # Expo (React Native) tablet POS
├── services/                 # backend domain services (microservices migration target)
│   ├── gateway/                # nginx reverse proxy — single stable base URL for all frontends
│   ├── auth/                    # businesses, locations, users, JWT issuance/refresh, PIN login
│   ├── catalog/                  # menu categories/items/modifiers, discounts
│   ├── ordering/                  # tables, orders/order-items lifecycle, discount application
│   ├── payments/                   # payment recording, split/partial payments, order paid-status transition
│   ├── staff/                       # staff CRUD, cash-drawer shift open/close/current/list
│   ├── printing/                    # printer CRUD, menu-item-to-printer routing rules
│   ├── reporting/                  # revenue/order summary analytics (top items, channel/status breakdowns), audit event log
│   ├── ai/                            # stateless AI orchestrator — intent classification, confirmed-action dispatch, menu import (no owned DB)
│   └── _shared/                   # small internal lib (JWT verify, HTTP client) — consumed by services/ai
├── packages/                 # shared frontend code
│   ├── types/                  # @smartserve/types — shared TS types + Zod schemas
│   ├── api-client/               # @smartserve/api-client — typed fetch client (points at the gateway)
│   ├── ui/                        # @smartserve/ui — shared shadcn/ui primitives (web + orders)
│   └── config/                     # @smartserve/config — shared eslint-config/tsconfig/tailwind-config
└── docs/
    ├── architecture.md          # product vision, tech stack, DB schema, AI design
    └── microservices-plan.md      # folder-tree optimization + step-by-step service extraction plan
```

## Tech stack

**Backend**: FastAPI (Python 3.14), SQLAlchemy 2.x (async), Alembic, PostgreSQL 16, Redis 7, RabbitMQ
(cross-service event bus), JWT auth, Anthropic Claude API, Docker.

**Web admin (`apps/web`)**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query,
Zustand, React Hook Form + Zod, next-intl (Hebrew/English RTL).

**Tablet POS (`apps/pos`)**: Expo (React Native) SDK 52+, TypeScript, Expo Router, NativeWind, TanStack Query,
expo-sqlite for offline order queueing.

**Monorepo tooling**: pnpm workspaces + Turborepo, `pnpm@11.18.0`.

## Getting started

### Prerequisites
- Node.js 22+, pnpm 11+
- Python 3.14+
- Docker + Docker Compose

### Local development (Docker Compose)

```bash
cp .env.example .env               # fill in SECRET_KEY; ANTHROPIC_API_KEY optional
python scripts/demo.py             # compose up, migrate, seed demo data
python scripts/demo.py --rebuild   # also rebuild images
python scripts/demo.py --reset     # wipe volumes first (fresh database)
```

`python scripts/demo.py` is the one-command start for a fresh clone. It brings up Postgres, Redis, RabbitMQ,
every backend service (each runs `alembic upgrade head` on boot), the `gateway`, and the web apps, then seeds
the demo tenant (`owner@demo.com` / `demo1234`) plus a small Hebrew menu, tables, printers and `HAPPY10`.

The optional local GGUF for `ai` is mounted from `${LOCAL_MODEL_DIR:-./models}` (gitignored). Leave
`LOCAL_MODEL_PATH` empty to skip the local model and use Haiku/Sonnet only.

Frontends should point at the gateway:

Catalog, ordering, payments, staff, printing, reporting and ai all publish/consume events on a shared durable
topic exchange (`smartserve.events`) over RabbitMQ — e.g. `order.created`/`order.updated`/`order.item_fired`,
`payment.completed`, `catalog.item_updated`, `staff.created`/`staff.updated`, `ai.action_executed`. `printing`
consumes `order.item_fired` to create print jobs, `ordering` consumes `payment.completed` to mark orders paid,
and `reporting` consumes every event (`#` wildcard) into an audit log (`EventLog`) and keeps its own Order
mirror in sync for analytics.

| Service | URL |
|---|---|
| Gateway (single API base URL for all frontends) | http://localhost:8080 |
| `services/auth` (direct) | http://localhost:8001 |
| `services/catalog` (direct) | http://localhost:8002 |
| `services/ordering` (direct) | http://localhost:8003 |
| `services/payments` (direct) | http://localhost:8004 |
| `services/staff` (direct) | http://localhost:8005 |
| `services/printing` (direct) | http://localhost:8006 |
| `services/reporting` (direct) | http://localhost:8007 |
| `services/ai` (direct) | http://localhost:8008 |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

### Frontend/monorepo commands (from repo root)

```bash
pnpm install
pnpm dev          # turbo run dev — all apps
pnpm build        # turbo run build
pnpm lint         # turbo run lint
pnpm typecheck    # turbo run typecheck
pnpm test         # turbo run test
pnpm format       # prettier --write
```

From the repo root, `python scripts/check.py` runs the same per-service and per-app checks CI expects
(ruff, mypy, pytest; typecheck, lint, vitest, `next build`). Examples:

```bash
python scripts/check.py --changed          # services/apps touched on this branch vs main
python scripts/check.py --services auth,catalog
python scripts/check.py --frontend web,orders
python scripts/check.py --all
```

### Backend service commands (from each service directory, e.g. `services/auth`, `services/catalog`, `services/ordering`, `services/payments`, `services/staff`, `services/printing`, `services/reporting`, `services/ai`)

```bash
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt
```

`services/ai` additionally depends on the local `services/_shared` package, which must be installed editable
before its own requirements:

```bash
pip install -e ../_shared -r requirements.txt -r requirements-dev.txt
```

```bash
ruff check --fix app/ tests/ && ruff format app/ tests/
mypy app/ --ignore-missing-imports --explicit-package-bases
pytest -q
```

Each service's test suite runs against an in-memory SQLite DB (`sqlite+aiosqlite:///:memory:`) — no running
Postgres required for tests.

## Backend architecture status

`apps/api` started as a single FastAPI monolith and was incrementally split into independently deployable
services under `services/`, one domain at a time, always on the same physical Postgres instance
(schema-per-service, no new infra), then retired entirely — see
[docs/microservices-plan.md](docs/microservices-plan.md) for the full rationale, service-boundary table, and
step-by-step plan.

| Step | Service | Status |
|---|---|---|
| 14 | `packages/ui` + `packages/config` extraction | ✅ done |
| 15 | `apps/api` modular monolith reorg (`app/modules/*`) | ✅ done |
| 16 | `services/gateway` (nginx) + `services/_shared` scaffold | ✅ done |
| 17 | `services/auth` extraction | ✅ done |
| 18 | `services/catalog` extraction | ✅ done |
| 19 | `services/ordering` extraction | ✅ done |
| 20 | `services/payments` extraction | ✅ done |
| 21 | `services/staff` extraction | ✅ done |
| 22 | `services/printing` extraction | ✅ done |
| 23 | `services/reporting` extraction | ✅ done |
| 24 | `services/ai` extraction | ✅ done |
| 25 | Retire the `apps/api` monolith | ✅ done |

All backend domains have been extracted into independently deployable `services/*` FastAPI apps; `apps/api`
no longer exists in the repo. The `gateway` (nginx) routes every `/api/v1/*` path prefix directly to its
owning service (see [services/gateway/nginx.conf](services/gateway/nginx.conf)), including a real-time
order/KDS WebSocket endpoint (`/api/v1/ws/{location_id}`), which was migrated to `services/ordering` as the
natural owner of order/KDS state changes.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR: TypeScript typecheck + lint for the JS/TS
workspace, and Python lint (`ruff`) + format-check for the backend.

## Contributing / workflow convention

Each unit of work (feature or migration step) is done on its own branch, validated (lint/typecheck/tests +
relevant build checks), merged into `main` with `--no-ff`, and pushed — see the step table above and
[docs/microservices-plan.md §6](docs/microservices-plan.md) for the exact pattern used throughout this
project's history.
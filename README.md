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
│   ├── pos/                    # Expo (React Native) tablet POS
│   └── api/                     # FastAPI monolith (being retired module-by-module, see below)
├── services/                 # backend domain services (microservices migration target)
│   ├── gateway/                # nginx reverse proxy — single stable base URL for all frontends
│   ├── auth/                    # businesses, locations, users, JWT issuance/refresh, PIN login
│   ├── catalog/                  # menu categories/items/modifiers, discounts
│   ├── ordering/                  # tables, orders/order-items lifecycle, discount application
│   ├── payments/                   # payment recording, split/partial payments, order paid-status transition
│   └── _shared/                   # small internal lib (JWT verify, HTTP client, event helpers) — scaffolded, not yet consumed
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

**Backend**: FastAPI (Python 3.14), SQLAlchemy 2.x (async), Alembic, PostgreSQL 16, Redis 7, JWT auth,
Anthropic Claude API, Docker.

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
cp .env.example .env               # fill in SECRET_KEY, ANTHROPIC_API_KEY
cp apps/api/.env.example apps/api/.env

docker compose up -d --wait
```

This starts Postgres, Redis, the `api` monolith, the extracted `auth`, `catalog`, `ordering` and `payments`
services, and the `gateway` (nginx) in front of them all. Frontends should point at the gateway:

| Service | URL |
|---|---|
| Gateway (single API base URL for all frontends) | http://localhost:8080 |
| `apps/api` (monolith, direct) | http://localhost:8000 |
| `services/auth` (direct) | http://localhost:8001 |
| `services/catalog` (direct) | http://localhost:8002 |
| `services/ordering` (direct) | http://localhost:8003 |
| `services/payments` (direct) | http://localhost:8004 |
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

### Backend service commands (from each service directory, e.g. `apps/api`, `services/auth`, `services/catalog`, `services/ordering`, `services/payments`)

```bash
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt

ruff check --fix app/ tests/ && ruff format app/ tests/
mypy app/ --ignore-missing-imports --explicit-package-bases
pytest -q
```

Each service's test suite runs against an in-memory SQLite DB (`sqlite+aiosqlite:///:memory:`) — no running
Postgres required for tests.

## Backend architecture status

`apps/api` started as a single FastAPI monolith and is being incrementally split into independently
deployable services under `services/`, one domain at a time, always on the same physical Postgres instance
(schema-per-service, no new infra) — see [docs/microservices-plan.md](docs/microservices-plan.md) for the
full rationale, service-boundary table, and step-by-step plan.

| Step | Service | Status |
|---|---|---|
| 14 | `packages/ui` + `packages/config` extraction | ✅ done |
| 15 | `apps/api` modular monolith reorg (`app/modules/*`) | ✅ done |
| 16 | `services/gateway` (nginx) + `services/_shared` scaffold | ✅ done |
| 17 | `services/auth` extraction | ✅ done |
| 18 | `services/catalog` extraction | ✅ done |
| 19 | `services/ordering` extraction | ✅ done |
| 20 | `services/payments` extraction | ✅ done |
| 21 | `services/staff` extraction | ⬜ not started |
| 22 | `services/printing` extraction | ⬜ not started |
| 23 | `services/reporting` extraction | ⬜ not started |
| 24 | `services/ai` extraction | ⬜ not started |
| 25 | Retire the `apps/api` monolith | ⬜ not started |

Until a domain is extracted, it still lives in `apps/api/app/modules/<domain>` and is routed to directly by
the gateway; once extracted it gets its own `services/<domain>` FastAPI app, Dockerfile, and trimmed model
set, and the gateway's nginx config is updated to route that domain's path prefixes to the new service.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR: TypeScript typecheck + lint for the JS/TS
workspace, and Python lint (`ruff`) + format-check for the backend.

## Contributing / workflow convention

Each unit of work (feature or migration step) is done on its own branch, validated (lint/typecheck/tests +
relevant build checks), merged into `main` with `--no-ff`, and pushed — see the step table above and
[docs/microservices-plan.md §6](docs/microservices-plan.md) for the exact pattern used throughout this
project's history.
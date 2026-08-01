# SmartServe — Architecture Document

> Last updated: 2026-07-31
> This file is the living reference for the entire SmartServe project.

---

## 1. Product Vision

SmartServe is a next-generation restaurant and commercial POS system targeting the Israeli market (primary competitors: Tabit, BeecommCloud). The core differentiator is an **AI-powered management backend** that allows non-technical restaurant managers and owners to perform all configuration tasks (menu creation, price adjustments, printer routing, staff management) through natural language — eliminating the complexity barrier present in all existing Israeli POS systems.

---

## 2. Key Design Principles

1. **AI efficiency first** — Use Claude Haiku for intent classification (cheap), Claude Sonnet only for complex reasoning. Never send more context than necessary.
2. **Offline resilience** — Tablet POS must work offline and sync when reconnected.
3. **RTL-native** — Hebrew is a first-class language. All UI components must support RTL from day one.
4. **Multi-tenant from day one** — Every entity is scoped to a `business_id` + `location_id`.
5. **Real-time everywhere** — Order updates, KDS, stock changes propagate via WebSockets.

---

## 3. Technology Stack

### 3.1 Backend
| Layer | Technology | Reason |
|-------|-----------|--------|
| Framework | **FastAPI** (Python 3.14) | Async, auto-OpenAPI docs, excellent for AI integration |
| Database | **PostgreSQL 16** | Relational, JSONB for flexible attributes |
| ORM | **SQLAlchemy 2.x** (async) | Type-safe, async support |
| Migrations | **Alembic** | Standard migration tool for SQLAlchemy |
| Cache / Pub-Sub | **Redis 7** | Order broadcasting, session caching, rate limiting |
| Task Queue | **Celery + Redis** | Background tasks (reports, email) |
| Real-time | **WebSockets** (FastAPI native) | KDS updates, order status |
| Auth | **JWT** (access + refresh tokens) | Stateless, mobile-friendly |
| AI | **Anthropic Claude API** | Haiku for intent classification, Sonnet for complex tasks |
| Payments | Abstract `PaymentProvider` interface | Ready for Cardcom / Tranzila / Stripe integration |
| Containerization | **Docker + Docker Compose** | Dev environment parity |

### 3.2 Frontend — Web Admin Dashboard
| Technology | Reason |
|-----------|--------|
| **Next.js 14** (App Router) | SSR, optimized for desktop, excellent DX |
| **TypeScript** | Full type safety |
| **Tailwind CSS** | RTL support via `dir` attribute, rapid UI |
| **shadcn/ui** | Accessible components, easy to customize |
| **TanStack Query** | Server state, caching, optimistic updates |
| **Zustand** | Lightweight client state (UI state only) |
| **React Hook Form + Zod** | Form validation with shared Zod schemas |
| **next-intl** | i18n with Hebrew (RTL) and English |

### 3.3 Frontend — Tablet POS App (iPad + Android)
| Technology | Reason |
|-----------|--------|
| **Expo (React Native)** SDK 52+ | True native on iPad & Android tablets |
| **TypeScript** | Full type safety |
| **Expo Router** | File-based routing (same pattern as Next.js) |
| **NativeWind** | Tailwind for React Native (consistent styling) |
| **TanStack Query** | Same API client pattern as web |
| **Zustand** | Order cart state, local session |
| **expo-sqlite** | Offline order queue |
| **i18n-js** | Hebrew/English with RTL |

### 3.4 Shared Packages (Turborepo)
| Package | Contents |
|---------|---------|
| `@smartserve/types` | All shared TypeScript interfaces and Zod schemas |
| `@smartserve/api-client` | Typed fetch client generated from FastAPI OpenAPI spec |
| `@smartserve/ui` | Shared web-only shadcn components (buttons, forms) |

---

## 4. Monorepo Structure

```
SmartServe/
├── apps/
│   ├── web/              # Next.js 14 admin dashboard
│   ├── pos/              # Expo React Native tablet POS
│   └── api/              # Python FastAPI backend
├── packages/
│   ├── types/            # @smartserve/types — shared TS types + Zod schemas
│   ├── api-client/       # @smartserve/api-client — typed fetch wrapper
│   └── ui/               # @smartserve/ui — shared web UI components
├── docs/
│   └── architecture.md   # This file
├── .github/
│   └── workflows/
│       └── ci.yml        # CI: lint, typecheck, test, build
├── turbo.json
├── pnpm-workspace.yaml
├── package.json          # Root workspace
└── README.md
```

---

## 5. Database Schema (Core Entities)

```
businesses (id, name, tax_id, country, currency, created_at)
  └── locations (id, business_id, name, address, timezone)
        ├── users (id, business_id, email, role, pin_hash, language)
        ├── menu_categories (id, location_id, name, name_he, sort_order, active)
        │     └── menu_items (id, category_id, name, name_he, price, tax_rate,
        │                     image_url, active, preparation_time_min)
        │           └── modifier_groups (id, item_id, name, name_he, required,
        │                                min_select, max_select)
        │                 └── modifiers (id, group_id, name, name_he, price_delta)
        ├── tables (id, location_id, name, capacity, section, active)
        ├── orders (id, location_id, table_id, status, channel, total, created_at)
        │     └── order_items (id, order_id, menu_item_id, qty, unit_price,
        │                      modifiers_json, notes, status)
        ├── payments (id, order_id, method, amount, status, gateway_ref)
        ├── printers (id, location_id, name, type, ip, port, active)
        │     └── printer_routes (id, printer_id, item_id)  -- route item→printer (an item may route to several)
        ├── inventory_items (id, location_id, menu_item_id, quantity, unit, threshold)
        └── staff_shifts (id, user_id, clock_in, clock_out, role)
```

---

## 6. AI Architecture (Token-Efficient)

### 6.1 Strategy — Minimize Token Usage
The AI is only invoked in the management dashboard (not in the POS app itself).

```
User types: "Add margherita pizza for 58 NIS in category Pizza"
     │
     ▼
[Step 1] Intent Classifier (Claude Haiku, ~200 tokens)
         System: "Classify the user request into one of N predefined intents.
                  Return JSON: {intent, confidence, extracted_params}"
         Result: {intent: "menu.create_item", params: {name: "Margherita Pizza",
                  price: 58, currency: "ILS", category_hint: "Pizza"}}
     │
     ▼
[Step 2] If confidence > 0.85: execute via API directly
         If confidence < 0.85: use Claude Sonnet for clarification (~800 tokens)
     │
     ▼
[Step 3] Show preview → user confirms → API call
```

### 6.2 AI Intents (complete list)
| Intent | Description |
|--------|-------------|
| `menu.create_item` | Add new menu item |
| `menu.update_item` | Change price/name/availability |
| `menu.bulk_price_change` | "Increase all drinks by 5%" |
| `menu.toggle_availability` | 86 an item / restore it |
| `menu.create_category` | Add new category |
| `menu.create_modifier_group` | Add size / topping group |
| `printer.route` | "Send pizzas to the kitchen printer" |
| `printer.troubleshoot` | "My printer isn't working" |
| `report.query` | "What were my best sellers last week?" |
| `staff.add_user` | Add employee |
| `staff.set_permissions` | Change role/access |
| `inventory.set_threshold` | "Alert me when beer drops below 5" |
| `settings.business` | Update business info |
| `help.general` | General guidance |

### 6.3 Token Budget Per Operation
| Operation | Model | Estimated Tokens | Cost (est.) |
|-----------|-------|-----------------|-------------|
| Intent classification | Haiku | ~300 in + 50 out | ~$0.0001 |
| Simple action execution | Haiku | ~500 in + 100 out | ~$0.0002 |
| Complex/ambiguous action | Sonnet | ~1000 in + 300 out | ~$0.004 |
| Report summary | Sonnet | ~2000 in + 500 out | ~$0.01 |

---

## 7. API Design

REST API with OpenAPI auto-documentation at `/docs`.

### Auth Endpoints
- `POST /auth/login` — email/password → JWT pair
- `POST /auth/pin` — PIN login for staff tablet
- `POST /auth/refresh` — refresh token

### Core Resource Endpoints (CRUD pattern)
- `/businesses/{id}` 
- `/locations/{id}`
- `/menu/categories`
- `/menu/items`
- `/menu/modifiers`
- `/tables`
- `/orders`
- `/payments`
- `/printers`
- `/staff`
- `/inventory`
- `/reports`

### AI Endpoint
- `POST /ai/command` — accepts `{message: string, context: {location_id, current_screen}}` → returns `{intent, params, preview, requires_confirmation}`
- `POST /ai/confirm` — confirm and execute a previewed action

### WebSocket
- `ws://api/ws/{location_id}` — real-time order/KDS events

---

## 8. Development Phases & Branches

| Step | Branch | Scope |
|------|--------|-------|
| 1 | `step/01-project-init` | Monorepo skeleton, tooling, CI, architecture.md |
| 2 | `step/02-backend-foundation` | FastAPI app, DB setup, auth, Docker Compose |
| 3 | `step/03-menu-management` | Menu CRUD API + web admin UI |
| 4 | `step/04-order-management` | Orders, tables, floor plan, WebSocket |
| 5 | `step/05-kitchen-display` | KDS app (tablet), printer routing |
| 6 | `step/06-payment-abstract` | Abstract payment layer, checkout flow |
| 7 | `step/07-pos-tablet-app` | Expo POS tablet app (order taking) |
| 8 | `step/08-ai-assistant` | AI command interface in web admin |
| 9 | `step/09-reporting` | Dashboard analytics, charts |
| 10 | `step/10-inventory` | Stock management, depletion alerts |
| 11 | `step/11-staff-management` | Shifts, permissions, clock-in |
| 12 | `step/12-multi-location` | Multi-location central management |
| 13 | `step/13-deployment` | Docker prod, CI/CD, env secrets |

---

## 9. RTL / Internationalization

- All text keys stored in `en.json` and `he.json`
- Hebrew (RTL) is the default for Israeli deployments
- CSS: `dir="rtl"` on `<html>`, Tailwind uses `rtl:` variant
- React Native: `I18nManager.forceRTL(true)` for Hebrew
- Dates: `date-fns` with `he` locale
- Currency: `Intl.NumberFormat('he-IL', {style: 'currency', currency: 'ILS'})`

---

## 10. Security Checklist (OWASP Top 10)

- [x] A01 Broken Access Control — RBAC on every API endpoint, location-scoped queries
- [x] A02 Cryptographic Failures — bcrypt for passwords, HTTPS only in production
- [x] A03 Injection — SQLAlchemy parameterized queries, Zod validation on all inputs
- [x] A04 Insecure Design — AI previews all changes before execution, audit log
- [x] A05 Security Misconfiguration — env vars only (no hardcoded secrets), CORS whitelist
- [x] A06 Vulnerable Components — Dependabot / pip-audit in CI
- [x] A07 Auth Failures — JWT short-lived (15min access, 7d refresh), PIN brute-force lockout
- [x] A08 Integrity Failures — Package lock files committed, CI verifies checksums
- [x] A09 Logging Failures — Structured logging (structlog), audit trail for all mutations
- [x] A10 SSRF — AI prompt inputs sanitized, no user-controlled URLs in server-side fetches

---

## 11. Key Decisions Log

| Date | Decision | Rationale |
|------|---------|-----------|
| 2026-07-31 | Next.js (web) + Expo (tablet) via Turborepo | Best per-platform UX, shared types |
| 2026-07-31 | Anthropic Claude (Haiku + Sonnet) | Cost-efficient with haiku for classification |
| 2026-07-31 | Abstract payment layer | No Israeli gateway API keys needed for dev |
| 2026-07-31 | Hebrew + English from day 1 | Target market is Israel, RTL complexity grows if added late |
| 2026-07-31 | FastAPI over Django | Async native, auto-OpenAPI for client generation, lighter weight |
| 2026-07-31 | PostgreSQL over MySQL | JSONB for modifiers, better full-text search for Hebrew |

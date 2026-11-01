# SmartServe review fix plan

This file is the work order for fixing every issue found in the October 2026 engineering, QA and design
review. Work through the items **in the order listed**, one branch and one pull request per item, and keep the
status table up to date so the work can be resumed at any time.

## Status

Update the row for each item in the same branch that fixes it. Status values: `todo`, `in progress`,
`merged`, `blocked (reason)`.

| # | ID | Branch | Status | PR |
| --- | --- | --- | --- | --- |
| 00 | SETUP | `chore/review-plan-and-check-runner` | merged | https://github.com/KKuznetsovV/SmartServe/pull/3 |
| 01 | E2 | `fix/e2-db-session-commit` | merged | https://github.com/KKuznetsovV/SmartServe/pull/4 |
| 02 | E8 | `refactor/e8-shared-backend-package` | merged | https://github.com/KKuznetsovV/SmartServe/pull/5 |
| 03 | E12 | `fix/e12-db-pool-sizing` | merged | https://github.com/KKuznetsovV/SmartServe/pull/6 |
| 04 | E1 | `fix/e1-migrations-and-demo-bootstrap` | merged | https://github.com/KKuznetsovV/SmartServe/pull/7 |
| 05 | QA-1 | `test/api-blackbox-suite` | merged | https://github.com/KKuznetsovV/SmartServe/pull/8 |
| 06 | QA-2 | `ci/full-pipeline` | merged | https://github.com/KKuznetsovV/SmartServe/pull/9 |
| 07 | E3 | `fix/e3-commit-before-response` | merged | https://github.com/KKuznetsovV/SmartServe/pull/10 |
| 08 | S1 | `fix/s1-tenant-scoping` | merged | https://github.com/KKuznetsovV/SmartServe/pull/11 |
| 09 | S6 | `fix/s6-scope-audit-log` | merged | https://github.com/KKuznetsovV/SmartServe/pull/13 |
| 10 | S2 | `fix/s2-role-hierarchy` | merged | https://github.com/KKuznetsovV/SmartServe/pull/14 |
| 11 | S3 | `fix/s3-server-side-pricing` | merged | https://github.com/KKuznetsovV/SmartServe/pull/15 |
| 12 | Q8 | `fix/q8-catalog-validation` | merged | https://github.com/KKuznetsovV/SmartServe/pull/16 |
| 13 | S7 | `chore/s7-upgrade-next-and-dependabot` | merged | https://github.com/KKuznetsovV/SmartServe/pull/17 |
| 14 | Q1 | `fix/q1-hydration-auth-guard` | merged | https://github.com/KKuznetsovV/SmartServe/pull/67 |
| 15 | S10 | `fix/s10-locale-cookie-validation` | merged | https://github.com/KKuznetsovV/SmartServe/pull/73 |
| 16 | Q7 | `fix/q7-dashboard-links` | merged | https://github.com/KKuznetsovV/SmartServe/pull/74 |
| 17 | E4 | `refactor/e4-single-owner-tables` | merged | https://github.com/KKuznetsovV/SmartServe/pull/76 https://github.com/KKuznetsovV/SmartServe/pull/78 https://github.com/KKuznetsovV/SmartServe/pull/79 |
| 17d | E4d | `refactor/e4d-users-owner-and-mirror-guard` | merged | https://github.com/KKuznetsovV/SmartServe/pull/82 |
| 18 | E5 | `feat/e5-transactional-outbox` | merged | https://github.com/KKuznetsovV/SmartServe/pull/84 |
| 18b | E5b | `fix/e5b-outbox-hardening` | merged | https://github.com/KKuznetsovV/SmartServe/pull/86 |
| 19 | E9 | `feat/e9-redis-ws-fanout` | merged | https://github.com/KKuznetsovV/SmartServe/pull/88 |
| 19b | E9b | `fix/e9b-ws-worker-id` | merged | https://github.com/KKuznetsovV/SmartServe/pull/90 |
| 20 | E6 | `fix/e6-atomic-order-totals` | merged | https://github.com/KKuznetsovV/SmartServe/pull/92 |
| 21 | E7 | `refactor/e7-decimal-money` | merged | https://github.com/KKuznetsovV/SmartServe/pull/94 |
| 22 | VAT | `feat/vat-inclusive-pricing` | merged | https://github.com/KKuznetsovV/SmartServe/pull/96 |
| 23 | Q4 | `fix/q4-cancelled-item-totals` | merged | https://github.com/KKuznetsovV/SmartServe/pull/98 |
| 24 | Q6 | `fix/q6-split-line-integrity` | merged | https://github.com/KKuznetsovV/SmartServe/pull/100 |
| 25 | Q5 | `fix/q5-payment-rules` | merged | https://github.com/KKuznetsovV/SmartServe/pull/101 |
| 26 | Q2 | `fix/q2-table-name` | merged | https://github.com/KKuznetsovV/SmartServe/pull/103 |
| 27 | Q3 | `fix/q3-print-on-send` | merged | https://github.com/KKuznetsovV/SmartServe/pull/105 |
| 28 | NUM | `feat/daily-order-numbers` | merged | https://github.com/KKuznetsovV/SmartServe/pull/107 |
| 29 | AI | `fix/ai-dry-run-preview` | merged | https://github.com/KKuznetsovV/SmartServe/pull/109 |
| 30a | S4a | `fix/s4a-device-registration` | merged | https://github.com/KKuznetsovV/SmartServe/pull/111 |
| 30b | S4b | `fix/s4b-ws-tickets` | merged | https://github.com/KKuznetsovV/SmartServe/pull/113 |
| 30c | S4c | `fix/s4c-public-display-token` | merged | https://github.com/KKuznetsovV/SmartServe/pull/115 |
| 31 | S5 | `fix/s5-pin-lockout-and-proxy-ip` | merged | https://github.com/KKuznetsovV/SmartServe/pull/117 |
| 31b | S5b | `fix/s5b-edge-client-ip` | merged | https://github.com/KKuznetsovV/SmartServe/pull/119 |
| 32 | S8 | `fix/s8-token-handling` | merged | https://github.com/KKuznetsovV/SmartServe/pull/120 |
| 33 | S9 | `fix/s9-ai-limits` | merged | https://github.com/KKuznetsovV/SmartServe/pull/121 |
| 34 | S11 | `fix/s11-secure-defaults` | merged | https://github.com/KKuznetsovV/SmartServe/pull/122 |
| 35 | E10 | `fix/e10-ai-nonblocking-inference` | merged | https://github.com/KKuznetsovV/SmartServe/pull/123 |
| 36 | E11 | `chore/e11-lock-dependencies` | merged | https://github.com/KKuznetsovV/SmartServe/pull/124 |
| 37 | E13 | `fix/e13-gateway-routing` | merged | https://github.com/KKuznetsovV/SmartServe/pull/125 |
| 38 | Q9 | `fix/q9-business-day-reports` | merged | https://github.com/KKuznetsovV/SmartServe/pull/126 |
| 39 | Q10 | `fix/q10-report-consistency` | merged | https://github.com/KKuznetsovV/SmartServe/pull/127 |
| 40 | UI-1 | `ui/pin-pad-ltr` | merged | https://github.com/KKuznetsovV/SmartServe/pull/128 |
| 41 | UI-2 | `ui/order-screen-localization-and-layout` | merged | https://github.com/KKuznetsovV/SmartServe/pull/129 |
| 42 | UI-3 | `ui/kds-redesign` | in progress | |
| 43 | UI-4 | `ui/floor-plan-live-status` | todo | |
| 44 | UI-5 | `ui/customer-display` | todo | |
| 45 | UI-6 | `ui/responsive-layouts` | todo | |
| 46 | UI-7 | `ui/accessibility` | todo | |
| 47 | E14 | `docs/e14-honest-readme-and-architecture` | todo | |

---

## Ground rules

1. **One item, one branch, one PR.** Never mix two items in one branch. If you notice an unrelated bug, add
   it to the *Discovered during fixes* list at the bottom of this file and keep going.
2. **Always branch from the latest `main`.** Each item starts only after the previous PR is merged.
3. **Don't change behaviour outside the item.** Refactors only where the item says so.
4. **Every fix gets a test that fails before the fix and passes after it.** Prefer the black-box API
   suite (`tests/api`, created in item 05) for anything that crosses services or depends on Postgres.
   When an item's regression test already exists as `xfail(strict=True)`, remove the marker in the fix
   branch.
5. **Database changes go through Alembic** in the service that owns the table. Never edit an existing
   migration. Every migration has a working `downgrade()`.
6. **No secrets in git.** Never commit `.env`, API keys or tokens. AI tests must mock Anthropic; no real key
   is needed for any check.
7. **Short, plain commit messages and comments.** Conventional subject line of 72 characters or fewer
   (`fix(payments): scope payments to caller's business`), a body of 1 to 5 lines saying what changed and why,
   and `Refs: review item S1`. No process narration in commits or code comments ("verified directly",
   "as the task asked", and so on).
8. **Do not merge these old branches wholesale:** `fix/db-session-commit-and-ai-bulk-trash`,
   `feature/ai-bulk-trash-by-category`, `feature/staff-deactivate-ai-intent`. Where an item below says to,
   take only the named hunks from them. Leave the branches themselves untouched.
9. **Never force-push `main`, never rewrite history, never delete existing branches.**
10. **If an item is blocked** (needs a product decision, a check can't be made green, or a tool is
    missing), stop that item: push the branch, open the PR as a draft, set the status to
    `blocked (reason)`, and continue with the next item that doesn't depend on it.
11. **Resuming:** if you are restarted or run low on context, re-read this file, run
    `gh pr list --state all --limit 100`, and continue from the first item not marked `merged`.

## Environment

- The host is Windows. Use Git Bash or PowerShell; every script you add must be cross-platform
  (write them in Python, not bash).
- Python **3.14** (the code relies on 3.14 syntax). Each service has its own `.venv`
  (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere).
- Node 22 and pnpm 11. Docker Desktop must be running. `gh auth status` must succeed.
- Preflight before item 00:
  - You are on `main` and `git pull --ff-only` succeeds.
  - `git status` is clean apart from `docs/review-fix-plan.md` (untracked; item 00 commits it) and
    `apps/*/tsconfig.tsbuildinfo` (generated; run `git restore` on them).
  - `python scripts/check.py --all` can't exist yet, so run the existing suites directly: `pytest` in every
    service and `pnpm turbo run typecheck lint test`. If `main` is not green before you start, stop and
    report.

## Per-item procedure

Run this for every item:

```bash
git switch main && git pull --ff-only
git switch -c <branch>
# implement the change and its tests
python scripts/check.py --changed          # created in item 00; see below
git add -A && git commit                   # message per rule 7
git push -u origin <branch>
gh pr create --base main --title "<conventional subject>" --body-file <tmp file>
gh pr checks --watch                       # fix and push again until green
gh pr merge --merge                        # merge commit, keeps the repo's --no-ff history
git switch main && git pull --ff-only
```

Each PR body contains: the review ID, the problem in one or two sentences, what changed, how it was tested
(commands and results), and before and after screenshots for UI items. Update the status table (status and
PR link) in a final commit on the branch before merging.

Checks that must pass before merging:

- Backend services touched: `ruff check`, `ruff format --check`, `mypy app/ --ignore-missing-imports
  --explicit-package-bases`, `pytest -q`.
- Frontend apps touched: `tsc --noEmit`, `next lint`, `vitest run`, `next build`.
- From item 05 onward, for any backend or gateway change: rebuild and restart the stack with
  `python scripts/demo.py --rebuild`, then run `pytest tests/api -q`.
- CI on the PR is green.

---

## Phase 0: setup

### 00 SETUP: commit this plan and add a check runner

Branch `chore/review-plan-and-check-runner`.

- Commit this file as `docs/review-fix-plan.md`.
- Add `scripts/check.py`, a cross-platform runner:
  - `--services auth,catalog,…` runs ruff check, ruff format --check, mypy and pytest in each service's
    venv. For `ai`, `_shared` must be on the path.
  - `--frontend web,orders` runs typecheck, lint, vitest and `next build`. Build `packages/types` and
    `packages/api-client` with tsup first.
  - `--api` runs `pytest tests/api` (only once item 05 exists).
  - `--changed` works out the services and apps to check from `git diff --name-only main...HEAD`.
    Changes in `services/_shared` or `services/gateway` mean all services.
  - `--all` runs everything.
  - Prints a summary table and exits non-zero on any failure.
- Make `pnpm install` succeed on pnpm 11, which the runner depends on. A clean `pnpm install` currently exits
  with `ERR_PNPM_IGNORED_BUILDS`: add an `allowBuilds` map to `pnpm-workspace.yaml` that sets the five
  packages listed in `onlyBuiltDependencies` to `true`. During preflight, if pnpm fails this way, make the
  same change locally first.
- Mention the script in the README's development section.

---

## Phase 1: make it true

### 01 E2: `staff`, `printing` and `reporting` never commit

Branch `fix/e2-db-session-commit`.

**Problem.** `get_db()` in `services/staff`, `services/printing` and `services/reporting`
(`app/db/session.py`) yields a session but never calls `commit()`. The API returns 201, but every write is
rolled back: staff create and update, PIN changes, deactivation, shift open and close, printers, routes, and
print jobs created by API calls. Confirmed by creating a printer (201) and finding 0 rows in Postgres.
`payments` was fixed earlier and has `tests/test_session_persistence.py`.

**Change.** Cherry-pick only the `session.py` changes for these three services from commit `0c637cf`
(branch `fix/db-session-commit-and-ai-bulk-trash`), or write the same try / commit / except-rollback
block.

**Tests.** Add `tests/test_session_persistence.py` to `staff` and `printing` modelled on the payments one:
the real `get_db`, a `StaticPool` SQLite engine, and a read through a fresh session after the request.
Cover creating a staff member, opening a shift, and creating a printer and a route.

### 02 E8: one shared backend package instead of copy-paste

Branch `refactor/e8-shared-backend-package`.

**Problem.** `deps.py`, `logging.py` and `router_base.py` exist in 8 copies, and `mq.py`, `security.py`
and `session.py` in 7. The copies have already drifted, which is how E2 survived. Two JWT libraries are in
use: `python-jose` (unmaintained) in the services and `PyJWT` in `_shared`.

**Change.**
- Turn `services/_shared` into an installable package `smartserve_shared` (`pyproject.toml`, `src/`
  layout or flat package, typed) with modules:
  - `db`: `make_engine(url, pool_size, max_overflow)`, `make_sessionmaker`, a `get_db` factory with
    commit and rollback, and `DeclarativeBase` helpers.
  - `security`: password hashing, `create_access_token`, `create_refresh_token`, and `decode_token`
    that checks `type`, all on PyJWT.
  - `deps`: `make_auth_dependencies(UserModel, get_db)` returning `get_current_user` and `require_role`,
    with the guards `require_manager`, `require_owner` and `require_staff`.
  - `mq`, `logging` (structlog; JSON when `ENVIRONMENT != development`), `routing` (the camelCase
    `APIRouter`), `schemas` (`BaseSchema`).
  - `app_factory.create_service_app(name, settings, api_router, lifespan_hooks)`: CORS, security headers,
    `/api/v1/health`, the slowapi wiring, and an `X-Served-By: <service>` response header.
- Every service depends on it (`-e ../_shared` in requirements). Change each Dockerfile and its compose
  build context to `./services`, as `ai` already does.
- Delete the per-service copies. Remove `python-jose` from every requirements file.
- Behaviour must not change: all existing tests pass unchanged, apart from import paths.

### 03 E12: connection pool sizing

Branch `fix/e12-db-pool-sizing`.

**Problem.** Each of 7 services allows `pool_size=10, max_overflow=20`, up to 210 connections against
Postgres' default limit of 100.

**Change.** Read `DB_POOL_SIZE` (default 5) and `DB_MAX_OVERFLOW` (default 5) in the shared `db` module,
and document them in `.env.example`.

### 04 E1: a fresh clone must start

Branch `fix/e1-migrations-and-demo-bootstrap`.

**Problem.** Only `catalog`, `ordering` and `reporting` have Alembic chains. Running them on an empty
database creates 9 of the 17 tables, with no `businesses`, `locations`, `users`, `payments`, `shifts`,
`printers`, `printer_routes` or `print_jobs`, so login fails with a 500. The demo seed script was deleted
with `apps/api` (see `git show 3271183^:apps/api/app/db/seed.py`). Nothing runs migrations at container
start. The `ai` service mounts `../smartserve-agent-model/inference_gguf`, which doesn't exist in a fresh
clone.

**Change.**
- Add an Alembic setup to `auth`, `payments`, `staff` and `printing`, mirroring catalog's `env.py`: a
  per-service `version_table` and an `include_object` filter that limits it to owned tables. Add a
  `0001_baseline` that creates exactly the tables each owns, matching the current models.
- Container startup runs `alembic upgrade head` and then uvicorn, through a small entrypoint script per
  service. Services wait for the database to be healthy first.
- Seeding:
  - `services/auth/app/db/seed.py` (`python -m app.db.seed`) creates the demo business, location and users
    idempotently: owner `owner@demo.com` / `demo1234`, manager `manager@demo.com` / `demo1234` (PIN
    2222), waiter PIN 1234 and kitchen PIN 5678.
  - `--with-second-tenant` adds a second business `owner@other.com` / `other1234`, used by the API test
    suite.
  - `scripts/seed_demo.py` logs in as the owner through the gateway and creates the rest through the public
    API: 3 categories with Hebrew names, 7 items with Hebrew names, a modifier group, 8 tables, Kitchen
    and Bar printers with routes, and a `HAPPY10` discount.
- `scripts/demo.py [--rebuild] [--reset]`: `docker compose up -d --build --wait`, run the auth seed inside
  the auth container, run `seed_demo.py`, and print the URLs and demo logins. `--reset` runs
  `docker compose down -v` first.
- In compose, `LOCAL_MODEL_PATH` defaults to empty and the model volume is `${LOCAL_MODEL_DIR:-./models}`
  (gitignored), so a fresh clone needs nothing outside the repo.
- Document `python scripts/demo.py` as the one-command start in the README.

**Acceptance.** `docker compose down -v && python scripts/demo.py` on a clean checkout ends with every
health check green and a working owner login.

### 05 QA-1: black-box API test suite

Branch `test/api-blackbox-suite`.

**Problem.** Every service is tested alone on SQLite, with `get_db` overridden by one uncommitted session.
That hides missing commits, failures at commit time, foreign keys, concurrency and cross-service effects.

**Change.**
- Create `tests/api/` at the repo root (`pytest`, `pytest-asyncio`, `httpx`, `websockets`, and a
  `requirements.txt` for it). It runs against the gateway at `API_BASE_URL` (default
  `http://localhost:8080/api/v1`) after `python scripts/demo.py --reset` with the second tenant.
- Fixtures: tokens for owner, manager, waiter and kitchen in business A, and owner in business B; helpers
  to create an order, add items, submit, and set an item's status.
- In each SQLite `conftest.py`, also turn on foreign keys
  (`PRAGMA foreign_keys=ON` on connect) so unit tests stop hiding foreign-key errors.
- Add one regression test per review finding below, marked
  `@pytest.mark.xfail(strict=True, reason="<ID>")`, so the suite is green now and each fix branch removes
  its marker:

| ID | Test |
| --- | --- |
| E3 | Deleting a category that has items returns 409 and the category still exists. A failing commit never returns 2xx. |
| E4 | Over 20 orders, submit and then immediately mark every item `ready` as kitchen; after 1 s each order is `ready`. The review saw 4 of 20 reverted to `submitted`. |
| E6 | 20 concurrent `POST /orders/{id}/items` (Cola): stored `subtotal` equals the sum of the lines. The review saw ₪48 against ₪240. |
| S1 | Business B gets 404 for: `POST /payments` on A's order, `GET /orders/{A}/payments`, `GET` and `POST` A's shifts, `POST /printers` with A's location, and `GET` A's printers and routes. |
| S2 | A manager cannot PATCH their own role, cannot assign `owner`, cannot deactivate the owner, and `role: "superadmin"` returns 422. |
| S3 | A modifier sent with `priceDelta: -68` doesn't change the price (the server uses the DB price). `qty: -3` returns 422. A −50% item discount returns 422. |
| S4 | An anonymous WebSocket is rejected. The public display endpoint returns only number and status. `/auth/pin/staff` without a device token returns 401. |
| S6 | The audit log returns only the caller's business events. |
| Q2 | An order created with `tableId` returns `tableName`. |
| Q3 | Submitting an order with a routed course-1 item creates a print job. |
| Q4 | Cancelling an item from the KDS lowers the order total. |
| Q5 | Payment is rejected for a cancelled order, an empty order, an unsent order, and a card amount above the remaining balance. |
| Q6 | Splitting 1 unit off a 3-unit line with ₪30 off pro-rates the discount (₪20 and ₪10) and keeps the category on both rows. |
| Q8 | A negative price returns 422, a category parent cycle returns 400, and a reorder without `ids` returns 422. |
| S10 | A request with cookie `locale=fr` renders the page (200), not a 500 (frontend check through `next start`; may live in the Playwright suite instead). |

### 06 QA-2: CI that tests what matters

Branch `ci/full-pipeline`.

**Problem.** CI never lints or tests `apps/orders`, never builds the Docker images, never runs migrations
on Postgres, never runs E2E (it is gated on `vars.E2E_BASE_URL`), and doesn't audit dependencies. Both
`tsconfig.tsbuildinfo` files are committed and change on every typecheck.

**Change.**
- Add `apps/orders` to the lint and test jobs.
- A new `stack` job: `python scripts/demo.py --reset` (Compose on the runner), then `pytest tests/api`,
  then Playwright E2E against the running apps, then `docker compose logs` uploaded as an artifact on
  failure.
- A migration check: each Alembic chain upgrades on an empty database and `alembic check` reports no
  drift.
- `pip-audit` for each service and `pnpm audit --prod`, failing on high and critical findings.
- Fix the E2E smoke test that targets `/display` on the web app (the route lives in `apps/orders`).
- Remove `apps/*/tsconfig.tsbuildinfo` from git and add them to `.gitignore`.

### 07 E3: return success only after the commit

Branch `fix/e3-commit-before-response`.

**Problem.** FastAPI runs a yield dependency's teardown after the response is sent, so `get_db`'s commit
happens after the client already got its 2xx. Deleting a non-empty category returned 204 while the commit
failed (NOT NULL violation in the log). Permanently deleting a trashed item that is referenced by an old
order line returned 204 and the item stayed in trash.

**Change.**
- In `smartserve_shared.db` expose `DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]`
  and use it on every route. Check that the pinned FastAPI version supports `scope`; if it doesn't, raise
  the minimum version.
- A global exception handler maps `sqlalchemy.exc.IntegrityError` to 409 with a readable message.
- Catalog: `delete_category` returns 409 "Category has items or subcategories" when it isn't empty.
- Remove the E3 xfail markers.

### 08 S1: tenant scoping in `payments`, `staff` shifts and `printing`

Branch `fix/s1-tenant-scoping`.

**Problem.** None of these routes checks the caller's business. As business B, the review paid business
A's order (201, and A's order became `paid`), read A's payments, listed A's shifts, opened a cash shift at
A's location, and created and listed printers at A's location.

**Change.** A shared `verify_location_owned(db, location_id, business_id)` (move it into
`smartserve_shared` and use it everywhere it is currently copied), applied to:
- `payments`: resolve the order's location and check ownership on create, get and list.
- `staff` shifts: open, close (through the shift's location), current and list.
- `printing`: list, create, update and delete printers; routes (through the printer's location, and check
  that the routed item belongs to the same business); print jobs.

Return 404, not 403, for other tenants. Add the S1 API tests and a parametrised unit test per service.

### 09 S6: scope the audit log

Branch `fix/s6-scope-audit-log`.

**Problem.** `GET /events` (reporting) returns every business's events, including AI prompts, staff names
and payment amounts.

**Change.** Every published event payload includes `businessId`. Add an indexed `business_id` column to
`event_log`, filled from the payload, through a migration. `list_events` filters by the caller's business.
Expose it through the gateway as `/api/v1/audit/events` (keep `/events` on the service only).

### 10 S2: role hierarchy

Branch `fix/s2-role-hierarchy`.

**Problem.** `role` is free text. A manager PATCHed their own role to `owner` and then edited the business
(an owner-only route). `superadmin` was accepted, a 1-digit PIN was accepted, and a manager could
deactivate the owner.

**Change.**
- `Role = Literal["owner", "manager", "cashier", "waiter", "kitchen"]` with a rank.
- A caller can create or update only users whose role ranks strictly below their own (the owner can do
  anything except demote the last owner).
- Nobody can change their own role or deactivate themselves.
- PINs are 4 to 6 digits; passwords are at least 8 characters.
- Unique email comparison is case-insensitive.

### 11 S3: the server sets prices

Branch `fix/s3-server-side-pricing`.

**Problem.** `OrderItemCreate.modifiers[].priceDelta` comes from the client and is trusted, so a Burger
sent with `-68` was stored at ₪0. `qty: -3` was accepted (subtotal −₪84), and a −50% item discount raised a
₪94 line to ₪141.

**Change.**
- `add_item` and `update_item` take only `modifierId`s. Load the modifiers from the catalog tables
  (read-only), check that they belong to the item's groups and are active, and enforce each group's
  `min_select`, `max_select` and `required`. The name and price come from the DB.
- Pydantic bounds: `qty` from 1 to 99; item discount percent above 0 up to 100; fixed discount above 0;
  `guest_number` 1 or more; `fire_course` from 1 to 5.

### 12 Q8: catalog validation

Branch `fix/q8-catalog-validation`.

**Problem.** An item priced −₪50 was created. A category could be made its own grandparent (A → B → A).
`POST …/reorder` with no `ids` returned a 500. Bulk changes can push prices below zero.

**Change.**
- Prices and modifier deltas are bounded (price ≥ 0); names are 1 to 255 characters; `sort_order` ≥ 0.
- Cycle detection walks the ancestors on category update.
- Typed `ReorderRequest(ids: list[str])` bodies in catalog and ordering.
- `BulkPriceUpdate` requires exactly one of `change_pct` (−90 to 200) or `change_abs`, and the resulting
  price never goes below 0.

### 13 S7: upgrade Next.js and add Dependabot

Branch `chore/s7-upgrade-next-and-dependabot`.

**Problem.** Both apps pin `next` to `15.3.0`, which is affected by CVE-2025-66478 (React Server Components
remote code execution, CVSS 10). It is fixed in 15.3.6: <https://nextjs.org/blog/CVE-2025-66478>.

**Change.** Upgrade `next` and `eslint-config-next` in both apps to the latest patched 15.x, and React to
the patched matching version. Add `.github/dependabot.yml` covering pip (each service directory), npm (the
root workspace) and GitHub Actions, weekly.

### 14 Q1: reloading logs the user out

Branch `fix/q1-hydration-auth-guard`.

**Problem.** In `apps/web`, a reload or a new tab on any dashboard page redirects to `/login` even with a
valid session. In `apps/orders`, reloading sends the tablet to `/setup`. The layout guards
(`(dashboard)/layout.tsx`, `(app)/layout.tsx`) run before the persisted Zustand stores have hydrated.

**Change.** Add a `hasHydrated` flag through `persist`'s `onRehydrateStorage` (or
`useStore.persist.hasHydrated()`). Guards render the spinner until hydration and only then redirect. The
login page redirects to the app if the user is already logged in, and setup redirects to login if the
device is already configured. Add a Playwright test that reloads a protected page.

### 15 S10: invalid locale cookie crashes every page

Branch `fix/s10-locale-cookie-validation`.

**Problem.** `src/i18n/request.ts` in both apps uses the `locale` cookie directly in a dynamic import, so
`locale=fr` returns a 500 on every route.

**Change.** Whitelist `['he', 'en']` and fall back to `he`. Add a unit test.

### 16 Q7: dashboard links to routes that don't exist

Branch `fix/q7-dashboard-links`.

**Problem.** The web dashboard's recent orders, *New order* and *Floor plan* link to `/orders` and
`/tables` on the web app, and they all 404. The fix exists in commit `0c637cf` (NEXT_PUBLIC_ORDERS_URL).

**Change.** Take only the dashboard, `.env.example` and compose hunks for `NEXT_PUBLIC_ORDERS_URL` from
`0c637cf`, and point every orders-app link at it.

---

## Phase 2: make it correct

### 17 E4: one owner per table

Branch `refactor/e4-single-owner-tables`. Decision: **keep the services and give every table exactly one
writer.**

**Problem.** Seven services map `users`, and three write `orders`. `reporting/app/modules/reports/events.py`
upserts `orders` (status and total) from events. Because events are published before commit and processed
late, it overwrote newer kitchen status: 4 of 20 orders went from `ready` back to `submitted`, and 0 of 20
with reporting stopped. `payments` also writes `orders.status = "paid"`. Ordering's ORM declares
cross-service foreign keys (for example `order_items.menu_item_id → menu_items.id`), which make catalog's
permanent delete fail.

**Change.**
- Reporting owns new tables `reporting_orders` and `reporting_order_items`, created by a migration and
  backfilled once from `orders` and `order_items`. Its consumers write only these tables, and every report
  query reads them. Remove reporting's mappings of `orders` and `order_items`.
- Event handlers apply an update only if the event is newer than the stored row: carry `occurredAt` and a
  monotonically increasing `version` from ordering.
- `payments` stops writing `orders`. It computes "fully paid" from its own payments plus the order total,
  read through ordering's API (`GET /orders/{id}` with the caller's token) or a read-only mirror, then
  publishes `payment.completed`. Ordering's consumer marks the order paid. The payment response includes
  `orderFullyPaid` and `remaining` so the UI doesn't depend on timing.
- Mirror models (tables owned by another service) inherit a `ReadOnlyMirror` mixin. A SQLAlchemy
  `before_flush` listener raises if a mirror instance is new, dirty or deleted.
- Remove cross-service foreign keys from the ORM models, and add an ordering migration that drops those
  constraints if they exist (`IF EXISTS`). Order lines keep their name and price snapshots.
- Remove the E4 xfail marker.

### 18 E5: transactional outbox and dead-lettering

Branch `feat/e5-transactional-outbox`.

**Problem.** Events are published before the transaction commits, so a rollback still announces the
change and a crash after commit loses the event. Consumers `reject(requeue=False)` with no dead-letter
queue. If RabbitMQ is down at boot, `connect()` returns `None` and publishing stays off until restart.

**Change.**
- `smartserve_shared.outbox`: each publishing service gets an `<service>_outbox` table (through a
  migration). `enqueue(db, routing_key, payload)` writes in the request's transaction, adding `eventId`,
  `occurredAt` and `businessId`. A background relay publishes unsent rows with retries and marks them
  sent.
- Consumers: a dead-letter exchange with a bounded retry count, then a parking queue. Idempotency by
  storing processed `eventId`s per consumer.
- `GET /api/v1/ready` returns 503 when the DB or broker is unreachable. The publisher reconnects instead of
  staying off.
- Replace every direct `mq.publish` in routers with `enqueue`.

### 19 E9: real-time fan-out through Redis

Branch `feat/e9-redis-ws-fanout`.

**Problem.** WebSocket clients live in an in-process dict in `ordering/ws_router.py`, so a second worker or
replica misses events. Broadcasts also fire before commit, and `list.remove` can raise when broadcast
already dropped a dead socket.

**Change.** The outbox relay (or a post-commit hook) publishes to the Redis channel `ws:{locationId}`. Each
ordering worker subscribes and forwards to its local sockets. Use a set for connections and handle every
disconnect path. Add a test with two workers if practical, otherwise a unit test of the pub/sub bridge.

### 20 E6: atomic order totals

Branch `fix/e6-atomic-order-totals`.

**Problem.** Totals are updated incrementally (`_recalculate_totals`) with read-modify-write and no lock.
20 concurrent adds stored a ₪48 subtotal against ₪240 of lines. Tax uses the last added item's rate for the
whole order.

**Change.** Delete `_recalculate_totals`. Every mutation of an order or its lines loads the order with
`with_for_update()` and ends with one `recompute_totals(order)` derived from the non-cancelled lines,
comps, line discounts and the order discount. Remove the E6 xfail marker.

### 21 E7: decimal money

Branch `refactor/e7-decimal-money`.

**Problem.** Money is `Float` in every service, with float arithmetic and an epsilon of 0.01 in the
paid-in-full check.

**Change.** Migrations to `NUMERIC(10,2)` for prices, deltas, totals, payments, tips and shift cash (each
in its owning service). Use `Decimal` in Python with `ROUND_HALF_UP` at line level. API JSON stays numeric
(serialize `Decimal` as a JSON number) so the frontends and `@smartserve/types` keep working. Remove the
epsilon.

### 22 VAT: prices include VAT at 18%

Branch `feat/vat-inclusive-pricing`.

**Problem.** Each item has `tax_rate = 0.17`, and the order adds VAT on top of the menu price (a ₪68
Burger totalled ₪79.56). Israel's VAT has been 18% since 1 January 2025, and consumer prices must be shown
including VAT.

**Change.**
- `businesses.vat_rate` (NUMERIC, default 0.18), owned by auth, with a migration. Menu prices are
  VAT-inclusive.
- The order total is the sum of the lines minus discounts. `tax_amount` is the VAT contained in that
  total: `total − total / (1 + vat_rate)`, rounded once.
- Stop using the per-item `tax_rate`; keep the column but deprecate it in the schema.
- UI: the ticket shows the total with "incl. 18% VAT ₪X" as a breakdown, never "+17%". The rate shows on
  the settings page (owner can edit).
- Update the AI prompts and dispatch so a price means the shelf price.

### 23 Q4: cancelling an item doesn't change the bill

Branch `fix/q4-cancelled-item-totals`.

**Problem.** Cancelling an item through `PATCH /orders/{id}/items/{itemId}/status` (KDS) leaves the total
unchanged (₪93.60 before and after).

**Change.** The status path calls `recompute_totals` and emits `order.updated` when a line is cancelled.
Remove the xfail marker.

### 24 Q6: splitting a line for a guest corrupts it

Branch `fix/q6-split-line-integrity`.

**Problem.** `_split_item_for_quantity` doesn't copy `category_id`, `category_name`, the discount fields or
the comp fields. After assigning 1 of 3 Schnitzels to a guest, the remaining 2 kept the full ₪30 discount
and the new row lost its category.

**Change.** Copy every snapshot field, and pro-rate fixed discounts by quantity (percent discounts stay
percent). Then recompute. Remove the xfail marker.

### 25 Q5: payment rules

Branch `fix/q5-payment-rules`.

**Problem.** Payments were accepted on a cancelled order, as ₪5,000 on a ₪14 bill, and as ₪1 on an empty
order, which then became `paid`. A takeaway order paid without being sent never reached the kitchen.

**Change.**
- Payment is allowed only when the order is `submitted`, `preparing`, `ready` or `served`, has a total
  above 0, and has nothing unsent.
- The amount is at most the remaining balance. Cash may exceed it: store `tendered` and `change_due`.
- Serialize payments per order with `pg_advisory_xact_lock`.
- Accept an `Idempotency-Key` header.
- Add a manager-PIN void and refund endpoint that records a negative payment row and re-opens the order
  balance.
- Update the payment dialog in `apps/orders` to match. Remove the xfail marker.

### 26 Q2: kitchen and order lists never show the table

Branch `fix/q2-table-name`.

**Problem.** `OrderOut.table_name` exists but is never filled in, so the KDS, order list, order page and
dashboard all show only "dine-in".

**Change.** Load the table relationship and fill `tableName` in every order response, including the public
display payload where relevant. Remove the xfail marker.

### 27 Q3: course-1 items never print

Branch `fix/q3-print-on-send`.

**Problem.** `order.item_fired` is published only by `POST /fire-course`, so submitting an order (course 1)
creates no print jobs. The gateway doesn't route `/locations/{id}/print-jobs`, so it returned 404 through
nginx.

**Change.**
- On submit, emit `order.item_fired` (through the outbox) for every `pending` line. When items are added
  to an already-submitted order, emit for those items.
- Add the nginx location for `print-jobs`. Remove the xfail marker.

### 28 NUM: daily order numbers

Branch `feat/daily-order-numbers`.

**Problem.** Every screen shows UUID fragments (`#4A00BFE6`) as order numbers.

**Change.** An `order_number` integer, allocated per location per business day (a counter table with a row
lock, reset at the business-day cutoff from Q9, or midnight local until Q9 lands). Show `#47` on the KDS,
customer display, order list, order page and dashboard.

### 29 AI: preview exactly what will change

Branch `fix/ai-dry-run-preview`.

**Problem** (tested live with Haiku):
- "תעלה את כל המשקאות ב-10%" (raise all drinks 10%) previewed *drinks* but repriced all 8 items. The
  Hebrew hint didn't match the English category name, so `category_id` fell back to `None`, which means
  the whole location.
- "תעלה את המחיר של ההמבורגר ל-72" got a good preview and then a 404 on confirm, because `fuzzy_match`
  ignores `name_he`.
- "the salmon is 86 for tonight" changed the price to ₪86. In kitchen slang, 86 means sold out.
- "add Dana as a new waiter" got a confident preview and then a 501. 7 of the 19 intents in
  `SUPPORTED_INTENTS` aren't implemented.
- The confirmation card shows the raw intent name and "95%".

**Change.**
- `/ai/command` runs a **dry run**: resolve every target now and return
  `changes: [{entity, id, name, field, from, to}]`, a `scope` (`items`, `category` or `location`) and a
  human summary. Store the frozen change list in Redis with `user_id` and `business_id`. `/confirm`
  executes exactly that list after re-checking the business and that the rows haven't changed since.
- Matching uses `name` and `name_he` for items and categories. When a hint is given but doesn't match,
  return 422 with suggestions; never widen the scope.
- Unimplemented intents: `/command` returns `supported: false` with a message and no `executionId`.
- Add few-shot examples for "86 the salmon" and "the salmon is 86'd" mapping to
  `menu.toggle_availability`, in English and Hebrew.
- UI (`apps/web` AI page and `confirmation-card.tsx`): a localized intent label, a table of changes
  (old → new), a count, and a red warning when the scope is the whole location. Show confidence only as a
  "low confidence" note below the threshold.
- Tests: dispatch dry-run unit tests with mocked catalog clients for the four cases above.

### 30 S4: device pairing and authenticated real-time

Split into three sequential PRs: `fix/s4a-device-registration`, `fix/s4b-ws-tickets`,
`fix/s4c-public-display-token`.

**Problem.** `/api/v1/ws/{locationId}` accepts anonymous clients and streams every order event.
`/public/locations/{id}/orders` returns full orders (totals, notes, staff IDs, every line).
`/auth/pin/staff?locationId=` lists every staff name, role and ID. The location ID needed for all three is
in the customer display URL, on a screen facing guests. Device setup also asks staff to type a 36-character
location UUID.

**Change.**
- **Devices.** A manager registers a device for a location (`POST /locations/{id}/devices`, auth-owned
  table `devices` with a hashed token, a name, a type `pos`/`kds`/`display`, and `revoked_at`). The orders
  app setup screen becomes: manager email and password, pick a location, name the device. The app stores
  the device token. `/auth/pin/staff` and `/auth/pin` require a valid device token for that location.
- **WebSocket.** `POST /api/v1/ws/ticket` (requires login, checks the location) returns a one-time ticket
  valid for 60 s, stored in Redis. The socket connects with `?ticket=`. Display devices use their device
  token instead.
- **Public display.** `GET /public/display/orders` is authenticated by the display device token and returns
  only `{orderNumber, status, updatedAt}`. The display URL no longer contains the location ID.
- Update both apps. Remove the S4 xfail markers.

### 31 S5: PIN lockout and real client IPs

Branch `fix/s5-pin-lockout-and-proxy-ip`.

**Problem.** `MAX_PIN_ATTEMPTS` and `PIN_LOCKOUT_MINUTES` are defined but unused. slowapi keys on the
client IP, but behind nginx in Docker that is the gateway's IP (uvicorn only trusts `X-Forwarded-For` from
127.0.0.1), so all staff share one bucket. Limits are in memory per process. Manager-override PINs in
ordering have no limit.

**Change.**
- Per-user failure counters in Redis; lock for `PIN_LOCKOUT_MINUTES` after `MAX_PIN_ATTEMPTS`
  (423 with `Retry-After`). Use the same helper for manager overrides.
- uvicorn runs with `--proxy-headers --forwarded-allow-ips` set to the gateway's network.
- slowapi uses Redis storage.
- Tests for the lockout and for limits keyed on the forwarded IP.

### 31b S5b: overwrite client IP at the gateway

Branch `fix/s5b-edge-client-ip`.

nginx sets `X-Forwarded-For` to `$remote_addr` (never the caller's header). Optional
`TRUSTED_PROXY_CIDRS` turns on the realip module for a load balancer in front.

### 32 S8: token handling

Branch `fix/s8-token-handling`.

**Problem.** Access and 7-day refresh tokens are persisted in `localStorage`. Refresh tokens are never
rotated or revoked. `ai` trusts the role claim, so a demoted manager keeps rights there for up to
15 minutes. `verify_token` doesn't check the token type.

**Change.**
- Auth sets the refresh token as an httpOnly, Secure (outside dev), `SameSite=Strict` cookie scoped to
  `/api/v1/auth`.
- Rotation on every refresh, with `jti` and family tracking in Redis; reuse of an old token revokes the
  family. `POST /auth/logout` revokes.
- The access token lives in memory only, not persisted. On app load, call `/auth/refresh` with
  `credentials: 'include'`. Keep the Q1 hydration behaviour working.
- The shared `decode_token` requires `type == "access"`.
- `ai` re-checks that the user is active and has the role through a cached auth lookup (60 s TTL).

### 33 S9: AI cost limits

Branch `fix/s9-ai-limits`.

**Problem.** Any role, waiters included, can call `/ai/command`. The limiter is created but never applied.
Each request can make up to 3 model calls, and there is no per-business quota.

**Change.** Limit `/command` and the menu-import endpoints to managers. Apply a per-user rate limit keyed
on the JWT `sub` (default 20 per minute) and a per-business daily call budget in Redis
(`AI_DAILY_CALL_BUDGET`, default 500); return 429 when exceeded. Bind pending executions to the user and
business.

### 34 S11: secure defaults

Branch `fix/s11-secure-defaults`.

**Problem.** The default `SECRET_KEY` is refused only when `ENVIRONMENT=production`. Compose publishes
Postgres, Redis and RabbitMQ on the host with the password `smartserve`. There is no CSP, and the
deprecated `X-XSS-Protection` header is still set.

**Change.**
- Refuse the default or a short `SECRET_KEY` unless `ENVIRONMENT` is `development` or `test`.
- Infrastructure credentials come from `.env`, and infrastructure ports bind to `127.0.0.1`.
- Drop `X-XSS-Protection`, and add a CSP and `Permissions-Policy` in the shared app factory and in both
  Next apps (`headers()` in `next.config.ts`).

### 35 E10: AI inference must not block the event loop

Branch `fix/e10-ai-nonblocking-inference`.

**Problem.** `local_classifier.classify()` calls llama.cpp synchronously inside an async route, which
blocks every other request for the length of the inference. A new sync `Anthropic` client is created on
every request.

**Change.** Run `classify` through `asyncio.to_thread` behind a `threading.Lock` (llama.cpp isn't thread
safe). Use one module-level `AsyncAnthropic` client with a timeout. Add a test proving that a slow fake
classifier doesn't block `/health`.

### 36 E11: reproducible builds

Branch `chore/e11-lock-dependencies`.

**Problem.** Every Python requirement is `>=` with no lockfile, so builds can change silently between
installs.

**Change.** Each service gets `requirements.in` and `requirements-dev.in`, compiled with
`uv pip compile` (or pip-tools) to pinned `requirements*.txt`. Dockerfiles and CI install the pinned files.
Confirm that a clean `pnpm install --frozen-lockfile` still exits 0.

### 37 E13: gateway routing

Branch `fix/e13-gateway-routing`.

**Problem.** Some service routes aren't reachable through nginx, and compose publishes every service port
(8001–8008) on the host, so the gateway can be bypassed.

**Change.**
- A `tests/api` test reads each service's `openapi.json` (through the internal network, or a compose
  `exec`), requests one path per route prefix through the gateway, and checks the `X-Served-By` header.
- Add the missing nginx locations.
- Remove the `ports:` entries for the services. Add a `docker-compose.debug.yml` that publishes them for
  local debugging.

### 38 Q9: reports by business day in local time

Branch `fix/q9-business-day-reports`.

**Problem.** `dayRangeToIso` (`apps/web/src/lib/report-utils.ts`) and the reporting `_period_start` use
UTC midnight. In Tel Aviv a "today" report starts at 02:00 or 03:00 local time, so late bar sales land on
the wrong day. `Location.timezone` exists but is never used.

**Change.**
- `locations.business_day_cutoff` (TIME, default `05:00`), owned by auth, with a migration.
- Report endpoints accept dates (`YYYY-MM-DD`) and convert them to UTC ranges using the location's time
  zone and cutoff. The frontend sends dates, not instants.
- Tests around DST changes.

### 39 Q10: one definition of revenue

Branch `fix/q10-report-consistency`.

**Problem.** On *Reports → Today*, revenue counts paid orders only (₪95.94), while *Top items* counts every
non-cancelled order (about ₪1,000).

**Change.** Every revenue figure uses paid orders and is net of comps and discounts. Label the columns
clearly. Add an "open orders" figure where useful.

---

## Phase 3: UI and UX

Attach before and after screenshots (Hebrew, light) to every UI PR.

### 40 UI-1: the PIN pad is mirrored in Hebrew

Branch `ui/pin-pad-ltr`.

In Hebrew the keypad reads 3 2 1 and swaps backspace with *back*. Set `dir="ltr"` on the keypad grid only
(the labels stay localized). Add a component test.

### 41 UI-2: order screen

Branch `ui/order-screen-localization-and-layout`.

- Menu tiles and category tabs show `name_he` when the locale is `he`, through a shared
  `localizedName(entity, locale)` helper in `packages/ui`. Use it in both apps (menu, KDS, display,
  reports).
- A responsive tile grid: 3 to 4 columns on a tablet, tiles at least 64 px tall, the price on the tile.
- Unsent lines show "not sent" (distinct from "pending" in the kitchen).
- *Cancel order* moves to an overflow menu with a confirmation dialog.
- One `formatPrice` in `packages/ui` (always two decimals, `he-IL`) used everywhere. The dashboard shows
  exact totals.

### 42 UI-3: kitchen display

Branch `ui/kds-redesign`.

- A large header per ticket with the table (or takeaway) and `#orderNumber`.
- The ticket's age, measured from when it was sent (add `sent_at` to order lines when they move to
  `pending`): amber at 10 minutes, red at 15.
- A station filter (`?station=kitchen|bar`) driven by the printer routes, so drinks leave the kitchen
  screen.
- A "course 2 waiting" strip for held lines.
- Modifiers and notes in bold.
- Bump buttons at least 64 px tall, and a whole-ticket bump.

### 43 UI-4: floor plan with live status

Branch `ui/floor-plan-live-status`.

- `GET /locations/{id}/tables?include=status` returns, per table, its open order (status, guests, seated
  since, total).
- Cards are coloured by state (free, seated, ordered, food ready, waiting to pay), show time seated and the
  total, and open the order on tap.
- Lay tables out by `pos_x` and `pos_y`, with a grid fallback.
- *Edit* and *Delete* appear only in a manager-only "edit layout" mode; the server already requires a
  manager.

### 44 UI-5: customer display

Branch `ui/customer-display`.

Two columns, *Preparing* and *Ready*, with large order numbers readable from 3 m on a 1080p screen. No item
lists. A sound or highlight when an order becomes ready. Uses the display token from S4.

### 45 UI-6: responsive layouts

Branch `ui/responsive-layouts`.

- The admin sidebar (`w-60`) collapses into a drawer below `lg`, with a top bar and a menu button.
- The logo isn't truncated in RTL.
- Use logical properties (`border-e`, `ms-`, `ps-`) instead of `border-r` and similar.
- The orders app's top nav collapses into a menu on phones, so *Kitchen*, *Display* and *Logout* stay
  reachable.
- No horizontal scrolling at 390 px. Add Playwright checks at 390 px and 1180 px.

### 46 UI-7: accessibility

Branch `ui/accessibility`.

The review's axe-core run over 52 captures found 103 colour-contrast failures, 69 form fields without
labels (21 in the printer-routing matrix), 18 icon-only buttons with no name, 12 unnamed selects, and
login pages with no `<main>` or `<h1>`.

- Add `@axe-core/playwright` checks for the main screens of both apps to CI.
- Fix every critical and serious violation: aria-labels such as "Route Burger to Kitchen" on the matrix
  checkboxes, names on icon buttons, labels on selects, contrast tokens in both themes, and landmarks.

---

## Final

### 47 E14: honest README and architecture docs

Branch `docs/e14-honest-readme-and-architecture`.

- README: a one-line pitch, a *Status* table (works, in progress, planned), the one-command start
  (`python scripts/demo.py`) with demo logins, the real stack versions (Next.js 15.x, not 14), and an
  updated architecture diagram showing table ownership, the outbox and Redis fan-out. Add a test strategy
  section (unit, API black-box, E2E, axe) and a *Known limitations* section.
- `apps/pos` is clearly marked as planned.
- `docs/architecture.md`: remove `apps/api` and Celery, update the security checklist to what is actually
  implemented, and add an ADR "Single owner per table" explaining E4 and why the services were kept.

### Final verification

After item 47 is merged, on a clean clone of `main`:

1. `python scripts/demo.py --reset`
2. `python scripts/check.py --all` (every service, both apps, `tests/api` with **no** remaining `xfail`
   markers from this plan, Playwright E2E and axe).
3. Confirm the latest CI run on `main` is green.

Then post a final report with: the merged PR list, anything `blocked` and why, the *Discovered during
fixes* list, and these manual follow-ups that need the owner:

- Record a 30-second README GIF (order → KDS → display → payment).
- Write the one-page case study.
- Set up a hosted demo with a nightly reset.
- Decide what to do with the old unmerged feature branches (search filters, AI bulk trash by category,
  staff deactivate intent).
- Build the Expo POS MVP with an offline order queue.
- Rotate any API keys or secrets that were ever shared or committed.

## Discovered during fixes

- E4: the 20-order "mark ready then wait 1s" race did not reproduce on current `main` (all orders stayed
  `ready`). QA-1 ships that case as a passing API test without `xfail`.
- QA-2: `pnpm audit --prod --audit-level high` fails on Next.js 15.3.0 (S7) and on Expo/`apps/pos`
  advisories. The CI step runs and is visible, but is `continue-on-error` until S7. `pip-audit` still fails
  the job on high/critical Python findings.
- E3: permanently deleting a trashed menu item that still has modifier groups returns 409 because
  `modifier_groups.item_id` has no ORM/DB cascade. Modifier groups and modifiers are catalog-owned
  children of the item and should be deleted with it; only cross-service references (order lines)
  should block the delete. Fix on `fix/catalog-permanent-delete-cascade` after S1: `cascade="all,
  delete-orphan"` on the ORM relationships, `ON DELETE CASCADE` in a catalog migration, and a
  `tests/api` case that an item with a modifier group can be trashed then permanently deleted (204)
  with the groups gone afterwards.
- E6: recomputing from non-cancelled lines makes `test_q4_cancelling_item_lowers_total` pass, so its
  strict xfail was removed here (otherwise CI XPASS-fails). Q4 still owns emitting `order.updated` on
  cancel.
- UI-1: `python-lockfiles` started failing on `main` after Q10 because CI installed unpinned `uv` and
  `--check` drifted. The job now pins `uv==0.13.6` to match `scripts/lock_deps.py`.
- UI-2: owner `/login` is `10/minute`. Web + orders Playwright together exceed that unless they share
  one cached owner token per worker (`apps/orders/e2e/owner-session.ts`).

(Add items here as you find them. Don't fix them in an unrelated branch.)

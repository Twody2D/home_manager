# Architecture

## Overview

Home Manager is a **modular monolith**: one FastAPI process, one PostgreSQL database,
one deployable frontend bundle served by nginx. Modules are separated by Python
package boundaries (`home_manager/<module>/`), not by network calls — there is no
service mesh, message broker, or shared cache to operate. This matches the project's
actual scale (a two-person household) while keeping module boundaries clean enough to
split out later if that scale ever changes.

```
┌─────────────┐      /api/*       ┌──────────────┐        ┌────────────┐
│   Browser   │ ───────────────▶ │ nginx (8080)  │ ─────▶ │ FastAPI     │
│  (PWA, SW)  │ ◀─────────────── │ static + edge │ ◀───── │ (8000)      │
└─────────────┘                   └──────────────┘        └─────┬──────┘
                                                                  │
                                                            ┌─────▼──────┐
                                                            │ PostgreSQL │
                                                            └────────────┘
```

nginx is the only container with a public-facing port in production (behind a TLS
reverse proxy — see `OPERATIONS.md`). It serves the built static PWA and proxies
`/api/*` to the backend over the internal Docker network; the backend and database
are never exposed directly.

## Backend modules (`backend/src/home_manager/`)

Each module owns its own SQLAlchemy models, Pydantic schemas, service functions, and
FastAPI router. Cross-module calls go through a module's `service` layer, never
through another module's models directly, so a module can be reasoned about (and
tested) on its own.

| Module | Responsibility |
|---|---|
| `auth` | Registration, login, Argon2id password hashing, JWT access tokens, refresh-token rotation, per-IP+email login throttling |
| `users` | Household members (tenant-scoped) |
| `tasks` | Task CRUD, assignment, completion |
| `calendar` | Availability / calendar events |
| `preferences` | Per-user scheduling preferences (quiet hours, workload caps, etc.) |
| `planning` | Deterministic daily scheduler: hard-constraint filtering (`availability.py`) + a separate, named-weight scoring layer (`scoring.py`) — no LLM involved |
| `ai` | `LLMProvider` interface + `MockProvider`/`GeminiProvider`, selected via env (`LLM_PROVIDER`, `LLM_MODEL`) |
| `assistant` | Natural-language → typed intent → validated business action. LLM output is never trusted directly: raw text goes through the provider, then Pydantic validation, then normal service-layer authorization using the *session's* tenant/user, never anything the model said |
| `notifications` | Web Push (VAPID) subscriptions and delivery; best-effort, never fails the caller's request |
| `integrations/alice` | Yandex Alice (Dialogs) webhook adapter — protocol translation only, delegates to `assistant.service` |
| `smarthome` | `SmartHomeProvider` interface + `MockProvider`/`HomeAssistantProvider`, selected via env (`SMART_HOME_PROVIDER`) |
| `core` | Cross-cutting: `errors.py` (typed `AppError` → JSON error envelope), `request_id.py`, `logging.py` (structured JSON logs + access log) |
| `db` | Async SQLAlchemy engine/session factory |
| `api/v1` | Router wiring only — no logic |

## Multi-tenancy

Every tenant-owned table carries a `tenant_id`. It is **only ever read from the
authenticated session** (JWT claims → dependency-injected auth context) — request
bodies and query params can never set or override it. There is no cross-tenant query
path in the codebase; each service function scopes its queries by the caller's
`tenant_id` before doing anything else.

## Frontend (`frontend/src/`)

React + Vite + TypeScript SPA, Tailwind for styling, TanStack Query for server state,
`vite-plugin-pwa` (`injectManifest` strategy) for the service worker — a custom SW
(`src/sw.ts`) handles push notifications and offline navigation fallback, rather than
the fully generated default.

Pages: `LoginPage`, `RegisterPage`, `DashboardPage`, `TasksPage`, `CalendarPage`,
`PreferencesPage`, `AssistantPage`, `DevicesPage`.

Access tokens live in memory only; refresh tokens live in an HttpOnly+Secure+SameSite
cookie set by the backend. Nothing auth-related touches `localStorage`.

## Data flow example: the AI assistant

1. User types a message in `AssistantPage`.
2. Frontend calls `POST /api/v1/assistant/message` with the authenticated session.
3. `assistant.service` sends the raw text to the configured `LLMProvider`.
4. The provider's text response is parsed as JSON and validated against a Pydantic
   intent schema — anything that doesn't validate is rejected before it touches any
   business logic.
5. The validated intent is executed via the normal `tasks`/`calendar` service
   functions, authorized against the *session's* `tenant_id`/`user_id` — the LLM
   output never supplies identity or bypasses authorization.

The same pattern (adapter → existing service layer, zero business logic in the
adapter itself) is used for the Alice webhook and the smart-home providers.

## Observability

See `OPERATIONS.md` for logging, health checks, and backup/restore.

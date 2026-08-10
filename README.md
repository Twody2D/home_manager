# Home Manager

Персональная multi-tenant платформа управления домом: задачи, расписание, планирование дня,
AI-помощник, интеграция с Яндекс Алисой и умным домом, PWA для мобильных устройств.

## Статус

Проект в активной разработке. Завершены:

- Milestone 1 — repository, Docker, backend skeleton, PostgreSQL, health checks, CI, authentication
- Milestone 2 — tenant/users/tasks CRUD
- Milestone 3 — PWA (login, dashboard, tasks, daily view)
- Milestone 4 — calendar (availability), preferences
- Milestone 5 — planning engine (deterministic daily scheduler)
- Milestone 6 — AI provider abstraction (Mock/Gemini) + task-creation assistant
- Milestone 7 — web push notifications (task assignment alerts)
- Milestone 8 — Yandex Alice integration (webhook adapter over the assistant pipeline)

Далее — Milestone 9 (Home Assistant / умный дом).

## Архитектура

Modular monolith. Подробности — в `ARCHITECTURE.md` (появится по мере развития проекта).

## Стек

- **Backend**: Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, PostgreSQL
- **Frontend**: TypeScript, React, Vite, Tailwind CSS, TanStack Query, PWA
- **Infra**: Docker Compose, GitHub Actions

## Разработка

### Backend

Требуется [uv](https://docs.astral.sh/uv/) и Docker.

```bash
cp .env.example .env      # заполнить POSTGRES_PASSWORD и JWT_SECRET реальными значениями
docker compose up -d --build
docker compose exec backend python -m alembic upgrade head
```

Полный стек (Postgres + backend + nginx с собранным фронтендом) — на `http://localhost:8080`.
Backend напрямую (в обход nginx, для отладки API) — на `http://localhost:8000`, эндпоинты под
`/api/v1/` (`/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/auth/*`, `/api/v1/tasks`,
`/api/v1/users`, `/api/v1/calendar/events`, `/api/v1/preferences/me`, `/api/v1/planning/plan`,
`/api/v1/assistant/message`, `/api/v1/notifications/*`, `/api/v1/integrations/alice/*`).

Web push is disabled by default. To enable it locally, generate a VAPID keypair and set
`VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` in `.env`:

```bash
cd backend && uv run python scripts/generate_vapid_keys.py
```

Локальная разработка backend без Docker (Postgres всё равно поднимается контейнером):

```bash
cd backend
uv sync --dev
uv run alembic upgrade head   # с DATABASE_URL, указывающим на локальный Postgres
uv run pytest
uv run ruff check .
uv run mypy src
uv run uvicorn home_manager.app:app --reload
```

### Frontend

Требуется [Node.js](https://nodejs.org/) 24+.

```bash
cd frontend
npm install
npm run dev
```

Dev-сервер (`http://localhost:5173`) проксирует `/api` на `http://localhost:8000` — backend нужно
поднять отдельно. Подробности и остальные npm-скрипты — в `frontend/README.md`.

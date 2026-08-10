# Home Manager

Персональная multi-tenant платформа управления домом: задачи, расписание, планирование дня,
AI-помощник, интеграция с Яндекс Алисой и умным домом, PWA для мобильных устройств.

## Статус

Проект в активной разработке. Текущий этап: Milestone 1 (repository, Docker, backend skeleton,
PostgreSQL, health checks, CI, authentication).

## Архитектура

Modular monolith. Подробности — в `ARCHITECTURE.md` (появится по мере развития проекта).

## Стек

- **Backend**: Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic, PostgreSQL
- **Frontend**: TypeScript, React, Vite, Tailwind CSS, TanStack Query, PWA
- **Infra**: Docker Compose, GitHub Actions

## Разработка

Документация по локальному запуску появится вместе с backend-скелетом (см. `backend/README.md`).

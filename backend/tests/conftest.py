from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from home_manager.app import create_app
from home_manager.auth.rate_limit import login_rate_limiter
from home_manager.db.session import get_engine
from home_manager.smarthome.factory import get_smart_home_provider

RegisterHousehold = Callable[..., Awaitable[dict]]


@pytest.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    """Truncate tenant-owned tables so each test starts from a clean slate."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE tasks, calendar_events, finance_incomes, finance_subscriptions, "
                "user_preferences, push_subscriptions, "
                "alice_links, refresh_tokens, users, tenants RESTART IDENTITY CASCADE"
            )
        )
    login_rate_limiter.reset_all()
    # The mock smart home provider is a process-wide singleton (like a real
    # hub connection would be) with mutable device state — clear it so
    # tests don't see devices left on by a previous test.
    get_smart_home_provider.cache_clear()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def register_household() -> RegisterHousehold:
    """Register a new household (tenant) and return the token response body."""

    async def _register(client: AsyncClient, **overrides: str) -> dict:
        payload = {
            "household_name": "Test Household",
            "display_name": "Owner",
            "email": "owner@example.com",
            "password": "correct-horse-battery-staple",
            **overrides,
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _register

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from home_manager.app import create_app
from home_manager.auth.rate_limit import login_rate_limiter
from home_manager.db.session import get_engine


@pytest.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    """Truncate tenant-owned tables so each test starts from a clean slate."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE refresh_tokens, users, tenants RESTART IDENTITY CASCADE")
        )
    login_rate_limiter.reset_all()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

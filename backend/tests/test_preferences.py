from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


@pytest.mark.asyncio
async def test_get_preferences_creates_defaults_on_first_access(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.get("/api/v1/preferences/me", headers=_auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == owner["user"]["id"]
    assert body["energy_pattern"] == "steady"
    assert body["task_speed_multiplier"] == 1.0
    assert body["workplace"] is None


@pytest.mark.asyncio
async def test_update_preferences_persists(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.patch(
        "/api/v1/preferences/me",
        json={
            "energy_pattern": "morning",
            "workplace": "Пятёрочка",
            "task_speed_multiplier": 0.8,
            "working_hours_start": "09:00:00",
            "working_hours_end": "18:00:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["energy_pattern"] == "morning"
    assert body["workplace"] == "Пятёрочка"
    assert body["task_speed_multiplier"] == 0.8
    assert body["working_hours_start"] == "09:00:00"

    refetched = await client.get("/api/v1/preferences/me", headers=_auth_headers(owner))
    assert refetched.json()["energy_pattern"] == "morning"


@pytest.mark.asyncio
async def test_update_preferences_rejects_non_positive_speed(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.patch(
        "/api/v1/preferences/me",
        json={"task_speed_multiplier": 0},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_preferences_are_isolated_per_user(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await client.post(
        "/api/v1/users",
        json={
            "email": "lena@example.com",
            "display_name": "Lena",
            "password": "correct-horse-battery-staple",
        },
        headers=_auth_headers(owner),
    )
    lena_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    lena_tokens = lena_login.json()

    await client.patch(
        "/api/v1/preferences/me",
        json={"energy_pattern": "evening"},
        headers=_auth_headers(lena_tokens),
    )

    owner_prefs = await client.get("/api/v1/preferences/me", headers=_auth_headers(owner))
    lena_prefs = await client.get("/api/v1/preferences/me", headers=_auth_headers(lena_tokens))

    assert owner_prefs.json()["energy_pattern"] == "steady"
    assert lena_prefs.json()["energy_pattern"] == "evening"


@pytest.mark.asyncio
async def test_preferences_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/preferences/me")

    assert response.status_code == 401

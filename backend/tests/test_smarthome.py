from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


@pytest.mark.asyncio
async def test_list_devices_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/smarthome/devices")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_devices_returns_mock_devices(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.get("/api/v1/smarthome/devices", headers=_auth_headers(owner))

    assert response.status_code == 200
    devices = response.json()
    entity_ids = {d["entity_id"] for d in devices}
    assert entity_ids == {"light.living_room", "switch.kettle"}
    assert all(d["is_on"] is False for d in devices)


@pytest.mark.asyncio
async def test_turn_on_updates_device_state(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/smarthome/devices/light.living_room/command",
        json={"command": "turn_on"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_on"] is True
    assert body["state"] == "on"

    list_response = await client.get("/api/v1/smarthome/devices", headers=_auth_headers(owner))
    updated = next(d for d in list_response.json() if d["entity_id"] == "light.living_room")
    assert updated["is_on"] is True


@pytest.mark.asyncio
async def test_toggle_flips_current_state(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    first = await client.post(
        "/api/v1/smarthome/devices/switch.kettle/command",
        json={"command": "toggle"},
        headers=headers,
    )
    assert first.json()["is_on"] is True

    second = await client.post(
        "/api/v1/smarthome/devices/switch.kettle/command",
        json={"command": "toggle"},
        headers=headers,
    )
    assert second.json()["is_on"] is False


@pytest.mark.asyncio
async def test_unknown_device_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/smarthome/devices/light.nonexistent/command",
        json={"command": "turn_on"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SMART_HOME_DEVICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_disallowed_domain_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/smarthome/devices/lock.front_door/command",
        json={"command": "turn_on"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_command_rejects_invalid_value(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/smarthome/devices/light.living_room/command",
        json={"command": "explode"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_any_household_member_can_control_devices(
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

    response = await client.post(
        "/api/v1/smarthome/devices/light.living_room/command",
        json={"command": "turn_on"},
        headers=_auth_headers(lena_tokens),
    )

    assert response.status_code == 200
    assert response.json()["is_on"] is True

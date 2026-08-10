from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


@pytest.mark.asyncio
async def test_assistant_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/assistant/message", json={"message": "hi"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_task_message_creates_task_for_self(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={"message": "create task: water the plants, 15 minutes"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_id"] is not None
    assert "water the plants" in body["reply"].lower()

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(owner))
    tasks = tasks_response.json()["items"]
    assert len(tasks) == 1
    assert tasks[0]["id"] == body["task_id"]
    assert tasks[0]["assigned_to"] == owner["user"]["id"]
    assert tasks[0]["tenant_id"] == owner["user"]["tenant_id"]
    assert tasks[0]["duration_minutes"] == 15


@pytest.mark.asyncio
async def test_unrecognized_message_does_not_create_a_task(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={"message": "what's the weather like"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_id"] is None

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(owner))
    assert tasks_response.json()["items"] == []


@pytest.mark.asyncio
async def test_empty_message_is_rejected(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message", json={"message": ""}, headers=_auth_headers(owner)
    )

    assert response.status_code == 422

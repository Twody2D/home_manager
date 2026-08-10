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
async def test_schedule_message_proposes_but_does_not_save_events(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "schedule: 2026-08-11 09:00-18:00 working_hours, "
                "2026-08-12 09:00-18:00 working_hours"
            ),
            "client_now": "2026-08-10T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_id"] is None
    proposed = body["proposed_events"]
    assert len(proposed) == 2
    assert {event["event_type"] for event in proposed} == {"working_hours"}
    assert proposed[0]["start_at"].startswith("2026-08-1")

    # A create_schedule intent only proposes events for review — nothing is
    # written to the calendar until the caller confirms via the bulk endpoint.
    events_response = await client.get(
        "/api/v1/calendar/events",
        params={"ends_after": "2026-08-01T00:00:00Z"},
        headers=_auth_headers(owner),
    )
    assert events_response.json() == []


@pytest.mark.asyncio
async def test_schedule_message_rolls_overnight_shift_to_next_day(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "schedule: 2026-08-11 22:00-06:00 working_hours",
            "client_now": "2026-08-10T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    proposed = body["proposed_events"]
    assert len(proposed) == 1
    assert proposed[0]["start_at"][:10] == "2026-08-11"
    assert proposed[0]["end_at"][:10] == "2026-08-12"


@pytest.mark.asyncio
async def test_schedule_message_with_impossible_date_degrades_gracefully(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "schedule: 2026-02-30 09:00-18:00 working_hours",
            "client_now": "2026-08-10T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_id"] is None
    assert body["proposed_events"] is None


@pytest.mark.asyncio
async def test_empty_message_is_rejected(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message", json={"message": ""}, headers=_auth_headers(owner)
    )

    assert response.status_code == 422

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]

# Far enough in the future that "now" never clips the planning window during
# a test run, and fixed so assertions on exact slot times are deterministic.
PLAN_DATE = "2027-03-15"


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


async def _create_task(client: AsyncClient, owner: dict, **overrides: object) -> dict:
    payload: dict = {"title": "Task", **overrides}
    response = await client.post("/api/v1/tasks", json=payload, headers=_auth_headers(owner))
    assert response.status_code == 201, response.text
    return response.json()


async def _invite_member(client: AsyncClient, owner: dict, **overrides: str) -> dict:
    payload = {
        "email": "lena@example.com",
        "display_name": "Lena",
        "password": "correct-horse-battery-staple",
        **overrides,
    }
    response = await client.post("/api/v1/users", json=payload, headers=_auth_headers(owner))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_plan_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/planning/plan?date={PLAN_DATE}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_schedules_task_at_start_of_default_working_window(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await _create_task(
        client, owner, title="Vacuum", assigned_to=owner["user"]["id"], duration_minutes=60
    )

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == PLAN_DATE
    assert len(body["scheduled"]) == 1
    entry = body["scheduled"][0]
    assert entry["title"] == "Vacuum"
    assert entry["start_at"] == f"{PLAN_DATE}T09:00:00Z"
    assert entry["end_at"] == f"{PLAN_DATE}T10:00:00Z"
    assert body["unscheduled"] == []


@pytest.mark.asyncio
async def test_task_without_duration_is_unscheduled(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await _create_task(client, owner, title="Someday", assigned_to=owner["user"]["id"])

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scheduled"] == []
    assert len(body["unscheduled"]) == 1
    assert "duration" in body["unscheduled"][0]["reason"].lower()


@pytest.mark.asyncio
async def test_schedules_around_existing_calendar_event(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "meeting",
            "title": "Standup",
            "start_at": f"{PLAN_DATE}T09:00:00Z",
            "end_at": f"{PLAN_DATE}T10:00:00Z",
        },
        headers=_auth_headers(owner),
    )
    await _create_task(
        client, owner, title="Dishes", assigned_to=owner["user"]["id"], duration_minutes=30
    )

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    body = response.json()
    assert len(body["scheduled"]) == 1
    assert body["scheduled"][0]["start_at"] == f"{PLAN_DATE}T10:00:00Z"


@pytest.mark.asyncio
async def test_higher_priority_task_wins_scarce_time(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    # Default window is 09:00-21:00 (12h = 720 min); two 600-minute tasks
    # can't both fit, so priority must decide which one gets scheduled.
    await _create_task(
        client,
        owner,
        title="Low priority marathon",
        assigned_to=owner["user"]["id"],
        duration_minutes=600,
        priority="low",
    )
    await _create_task(
        client,
        owner,
        title="Urgent marathon",
        assigned_to=owner["user"]["id"],
        duration_minutes=600,
        priority="urgent",
    )

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    body = response.json()
    assert len(body["scheduled"]) == 1
    assert body["scheduled"][0]["title"] == "Urgent marathon"
    assert len(body["unscheduled"]) == 1
    assert body["unscheduled"][0]["title"] == "Low priority marathon"


@pytest.mark.asyncio
async def test_unreachable_deadline_reports_deadline_reason(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await _create_task(
        client,
        owner,
        title="Impossible deadline",
        assigned_to=owner["user"]["id"],
        duration_minutes=120,
        due_at=f"{PLAN_DATE}T09:30:00Z",
    )

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    body = response.json()
    assert body["scheduled"] == []
    assert len(body["unscheduled"]) == 1
    assert "deadline" in body["unscheduled"][0]["reason"].lower()


@pytest.mark.asyncio
async def test_only_own_assigned_tasks_are_planned(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    lena = await _invite_member(client, owner)
    await _create_task(
        client, owner, title="Lena's chore", assigned_to=lena["id"], duration_minutes=30
    )

    response = await client.get(
        f"/api/v1/planning/plan?date={PLAN_DATE}", headers=_auth_headers(owner)
    )

    body = response.json()
    assert body["scheduled"] == []
    assert body["unscheduled"] == []

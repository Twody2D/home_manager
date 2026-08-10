from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


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
async def test_create_event_belongs_to_current_user(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "working_hours",
            "title": "Work",
            "start_at": "2026-01-05T09:00:00Z",
            "end_at": "2026-01-05T17:00:00Z",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == owner["user"]["id"]
    assert body["event_type"] == "working_hours"


@pytest.mark.asyncio
async def test_create_event_rejects_invalid_window(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "meeting",
            "title": "Time travel",
            "start_at": "2026-01-05T17:00:00Z",
            "end_at": "2026-01-05T09:00:00Z",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_create_events(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/calendar/events/bulk",
        json={
            "events": [
                {
                    "event_type": "working_hours",
                    "title": "Work",
                    "start_at": "2026-01-05T09:00:00Z",
                    "end_at": "2026-01-05T18:00:00Z",
                },
                {
                    "event_type": "working_hours",
                    "title": "Work",
                    "start_at": "2026-01-06T09:00:00Z",
                    "end_at": "2026-01-06T18:00:00Z",
                },
            ]
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body) == 2
    assert all(event["user_id"] == owner["user"]["id"] for event in body)

    list_response = await client.get("/api/v1/calendar/events", headers=_auth_headers(owner))
    assert len(list_response.json()) == 2


@pytest.mark.asyncio
async def test_bulk_create_rejects_invalid_window_in_any_item(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/calendar/events/bulk",
        json={
            "events": [
                {
                    "event_type": "working_hours",
                    "title": "Work",
                    "start_at": "2026-01-05T09:00:00Z",
                    "end_at": "2026-01-05T18:00:00Z",
                },
                {
                    "event_type": "working_hours",
                    "title": "Backwards",
                    "start_at": "2026-01-06T18:00:00Z",
                    "end_at": "2026-01-06T09:00:00Z",
                },
            ]
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422
    list_response = await client.get("/api/v1/calendar/events", headers=_auth_headers(owner))
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_bulk_create_rejects_more_than_max_items(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    events = [
        {
            "event_type": "working_hours",
            "title": "Work",
            "start_at": "2026-01-05T09:00:00Z",
            "end_at": "2026-01-05T18:00:00Z",
        }
        for _ in range(61)
    ]

    response = await client.post(
        "/api/v1/calendar/events/bulk",
        json={"events": events},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_household_members_can_see_each_others_events(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    lena = await _invite_member(client, owner)
    lena_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    lena_tokens = lena_login.json()

    await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "sleep",
            "title": "Sleep",
            "start_at": "2026-01-05T22:00:00Z",
            "end_at": "2026-01-06T06:00:00Z",
        },
        headers=_auth_headers(lena_tokens),
    )

    response = await client.get("/api/v1/calendar/events", headers=_auth_headers(owner))

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["user_id"] == lena["id"]


@pytest.mark.asyncio
async def test_cannot_edit_another_members_event(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await _invite_member(client, owner)
    lena_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    lena_tokens = lena_login.json()

    create_response = await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "personal",
            "title": "Lena's plan",
            "start_at": "2026-01-05T10:00:00Z",
            "end_at": "2026-01-05T11:00:00Z",
        },
        headers=_auth_headers(lena_tokens),
    )
    event_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/calendar/events/{event_id}",
        json={"title": "Hijacked"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_EVENT_OWNER"


@pytest.mark.asyncio
async def test_event_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    create_response = await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "trip",
            "title": "A's trip",
            "start_at": "2026-01-05T10:00:00Z",
            "end_at": "2026-01-05T11:00:00Z",
        },
        headers=_auth_headers(owner_a),
    )
    event_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/calendar/events/{event_id}", headers=_auth_headers(owner_b)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_delete_own_event(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/calendar/events",
        json={
            "event_type": "sport",
            "title": "Run",
            "start_at": "2026-01-05T07:00:00Z",
            "end_at": "2026-01-05T08:00:00Z",
        },
        headers=_auth_headers(owner),
    )
    event_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/calendar/events/{event_id}", headers=_auth_headers(owner)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/calendar/events/{event_id}", headers=_auth_headers(owner)
    )
    assert get_response.status_code == 404

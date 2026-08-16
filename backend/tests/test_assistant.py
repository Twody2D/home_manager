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
async def test_unrecognized_message_replies_in_requested_locale(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={"message": "what's the weather like", "locale": "ru"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "полить цветы" in body["reply"]


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
async def test_schedule_message_uses_saved_workplace_as_default_title(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await client.patch(
        "/api/v1/preferences/me",
        json={"workplace": "Пятёрочка"},
        headers=_auth_headers(owner),
    )

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "schedule: 2026-08-11 09:00-18:00 working_hours",
            "client_now": "2026-08-10T12:00:00+03:00",
            "locale": "ru",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    assert proposed[0]["title"] == "Работа — Пятёрочка"


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
async def test_pattern_message_expands_every_matching_weekday(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # 2026-08-03 and 2026-08-31 are both Mondays — 4 full Mon-Fri weeks plus
    # the trailing Monday, so 21 matching weekdays in total.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4,5 from=2026-08-03 to=2026-08-31 "
                "09:00-18:00 working_hours"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    proposed = body["proposed_events"]
    assert len(proposed) == 21
    late_dates = {
        event["start_at"][:10] for event in proposed if event["start_at"][:10] > "2026-08-29"
    }
    assert late_dates == {"2026-08-31"}
    assert all(event["start_at"][11:16] == "09:00" for event in proposed)


@pytest.mark.asyncio
async def test_pattern_message_mentioning_weekend_restores_dropped_friday(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # 2026-08-03 is a Monday. A small model reliably mistakes "выходных" as
    # including Friday and returns weekdays=[1,2,3,4] — this should be
    # corrected back to include Friday since the message talks about the
    # weekend.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4 from=2026-08-03 to=2026-08-07 "
                "09:00-18:00 working_hours кроме выходных"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = {event["start_at"][:10] for event in proposed}
    assert len(proposed) == 5
    assert "2026-08-07" in dates


@pytest.mark.asyncio
async def test_pattern_message_mentioning_weekend_restores_full_week_from_narrower_subset(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # Same bug, worse: seen live returning weekdays=[1,2,3] (Mon-Wed only)
    # for a "кроме выходных" request — any weekday subset short of the full
    # Mon-Fri week should be restored, not just the exact [1,2,3,4] case.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3 from=2026-08-03 to=2026-08-07 "
                "09:00-18:00 working_hours кроме выходных"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = {event["start_at"][:10] for event in proposed}
    assert len(proposed) == 5
    assert {"2026-08-06", "2026-08-07"} <= dates


@pytest.mark.asyncio
async def test_pattern_message_without_weekend_mention_is_not_corrected(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # Same weekdays=[1,2,3,4] as above, but nothing in the message mentions
    # the weekend — a genuine Mon-Thu request must be left alone.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4 from=2026-08-03 to=2026-08-07 09:00-18:00 working_hours"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = {event["start_at"][:10] for event in proposed}
    assert len(proposed) == 4
    assert "2026-08-07" not in dates


@pytest.mark.asyncio
async def test_pattern_message_skips_excluded_dates(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4,5 from=2026-08-03 to=2026-08-31 "
                "09:00-18:00 working_hours exclude=2026-08-12,2026-08-13"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = {event["start_at"][:10] for event in proposed}
    assert len(proposed) == 19
    assert "2026-08-12" not in dates
    assert "2026-08-13" not in dates


@pytest.mark.asyncio
async def test_pattern_message_with_no_matching_weekdays_degrades_gracefully(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # 2026-08-11 is a Tuesday; asking only for Saturdays (6) in a one-day
    # range matches nothing.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=6 from=2026-08-11 to=2026-08-11 09:00-18:00 working_hours"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["proposed_events"] is None


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
async def test_schedule_message_treats_24_00_as_midnight_next_day(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # A model may emit "24:00" for "until midnight" even though the prompt
    # tells it to use "00:00" — this should still land on the next day.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "schedule: 2026-08-12 12:00-24:00 working_hours",
            "client_now": "2026-08-10T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    assert len(proposed) == 1
    assert proposed[0]["start_at"][:10] == "2026-08-12"
    assert proposed[0]["end_at"][:10] == "2026-08-13"
    assert proposed[0]["end_at"][11:16] == "00:00"


@pytest.mark.asyncio
async def test_schedule_message_corrects_ordinal_day_drift(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # The live model has been observed drifting the day-of-month for a bare
    # "11-го"/"12-го" reference (e.g. onto the 13th/15th) while keeping
    # month/year and event order correct — simulate that drift here (mock
    # returns the 15th/16th) and confirm the ordinal day named in the
    # message ("11-го"/"12-го") wins.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "schedule: 2026-08-15 11:00-23:00 working_hours 11-го, "
                "2026-08-16 12:00-24:00 working_hours 12-го"
            ),
            "client_now": "2026-08-11T09:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = sorted(event["start_at"][:10] for event in proposed)
    assert dates == ["2026-08-11", "2026-08-12"]


@pytest.mark.asyncio
async def test_schedule_message_without_matching_ordinal_days_is_not_corrected(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # No ordinal-day wording in the message — the model's own dates must be
    # left alone, not overwritten.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "schedule: 2026-08-15 11:00-23:00 working_hours",
            "client_now": "2026-08-11T09:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    assert proposed[0]["start_at"][:10] == "2026-08-15"


@pytest.mark.asyncio
async def test_rotation_message_expands_work_off_cycle(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # 2/2 starting 2026-08-03: work Aug 3-4, off 5-6, work 7-8, off 9-10, ...
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "rotation: work=2 off=2 from=2026-08-03 to=2026-08-10 09:00-21:00 working_hours"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = sorted(event["start_at"][:10] for event in proposed)
    assert dates == ["2026-08-03", "2026-08-04", "2026-08-07", "2026-08-08"]


@pytest.mark.asyncio
async def test_schedule_message_without_time_gets_a_missing_time_reply(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": "no-time-schedule: 2026-08-11 working_hours",
            "client_now": "2026-08-01T12:00:00+03:00",
            "locale": "ru",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["task_id"] is None
    assert body["proposed_events"] is None
    assert "время" in body["reply"].lower()


@pytest.mark.asyncio
async def test_ratio_other_than_5_2_is_converted_from_workweek_to_rotation(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # Live testing showed the model returning a plain Mon-Fri pattern for
    # "2/2" instead of the rotating shift it actually describes — simulate
    # that here (mock returns weekdays=[1,2,3,4,5], same as a real "2/2"
    # misclassification) and confirm the "2/2" in the message text converts
    # it to a rotation instead of leaving it as every weekday.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4,5 from=2026-08-03 to=2026-08-10 "
                "09:00-21:00 working_hours работаю 2/2"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    dates = sorted(event["start_at"][:10] for event in proposed)
    assert dates == ["2026-08-03", "2026-08-04", "2026-08-07", "2026-08-08"]


@pytest.mark.asyncio
async def test_ratio_5_2_stays_a_plain_workweek(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4,5 from=2026-08-03 to=2026-08-07 "
                "09:00-21:00 working_hours работаю 5/2"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    proposed = response.json()["proposed_events"]
    assert len(proposed) == 5


@pytest.mark.asyncio
async def test_identical_start_and_end_time_is_treated_as_missing_time(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    # A model that fabricates a time instead of admitting it has none tends
    # to produce a zero-duration shift like this — never legitimate for a
    # real shift, so it's treated as "no time given" rather than proposed.
    response = await client.post(
        "/api/v1/assistant/message",
        json={
            "message": (
                "pattern: weekdays=1,2,3,4,5 from=2026-08-03 to=2026-08-07 "
                "09:00-09:00 working_hours"
            ),
            "client_now": "2026-08-01T12:00:00+03:00",
            "locale": "ru",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["proposed_events"] is None
    assert "время" in body["reply"].lower()


@pytest.mark.asyncio
async def test_empty_message_is_rejected(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/assistant/message", json={"message": ""}, headers=_auth_headers(owner)
    )

    assert response.status_code == 422

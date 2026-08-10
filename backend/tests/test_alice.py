from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


def _alice_request(utterance: str, session: dict | None = None) -> dict:
    return {
        "meta": {"locale": "ru-RU", "client_id": "test-client"},
        "request": {
            "command": utterance.lower(),
            "original_utterance": utterance,
            "type": "SimpleUtterance",
        },
        "session": session or {"session_id": "sess-1", "message_id": 0, "new": True},
        "version": "1.0",
    }


@pytest.mark.asyncio
async def test_token_endpoints_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/integrations/alice/token")).status_code == 401
    assert (await client.post("/api/v1/integrations/alice/token")).status_code == 401
    assert (await client.delete("/api/v1/integrations/alice/token")).status_code == 401


@pytest.mark.asyncio
async def test_status_is_unlinked_before_issuing_a_token(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.get("/api/v1/integrations/alice/token", headers=_auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert body["linked"] is False
    assert body["last_used_at"] is None


@pytest.mark.asyncio
async def test_issuing_a_token_links_the_account(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    issue_response = await client.post(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    assert issue_response.status_code == 200
    body = issue_response.json()
    assert body["token"]
    assert body["token"] in body["webhook_url"]

    status_response = await client.get(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    assert status_response.json()["linked"] is True


@pytest.mark.asyncio
async def test_webhook_without_token_replies_not_linked_but_returns_200(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/integrations/alice/webhook", json=_alice_request("create task: water plants")
    )

    assert response.status_code == 200
    body = response.json()
    assert "linked" in body["response"]["text"].lower()
    assert body["version"] == "1.0"
    assert body["session"]["session_id"] == "sess-1"


@pytest.mark.asyncio
async def test_webhook_with_unknown_token_replies_not_linked(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/integrations/alice/webhook?token=not-a-real-token",
        json=_alice_request("create task: water plants"),
    )

    assert response.status_code == 200
    assert "linked" in response.json()["response"]["text"].lower()


@pytest.mark.asyncio
async def test_webhook_create_task_utterance_creates_task_for_linked_user(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    issue_response = await client.post(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    token = issue_response.json()["token"]

    webhook_response = await client.post(
        f"/api/v1/integrations/alice/webhook?token={token}",
        json=_alice_request("create task: water the plants, 15 minutes"),
    )

    assert webhook_response.status_code == 200
    body = webhook_response.json()
    assert "water the plants" in body["response"]["text"].lower()
    assert body["response"]["end_session"] is False

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(owner))
    tasks = tasks_response.json()["items"]
    assert len(tasks) == 1
    assert tasks[0]["assigned_to"] == owner["user"]["id"]
    assert tasks[0]["tenant_id"] == owner["user"]["tenant_id"]

    status_response = await client.get(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    assert status_response.json()["last_used_at"] is not None


@pytest.mark.asyncio
async def test_revoking_token_disables_the_webhook(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    issue_response = await client.post(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    token = issue_response.json()["token"]

    revoke_response = await client.delete(
        "/api/v1/integrations/alice/token", headers=_auth_headers(owner)
    )
    assert revoke_response.status_code == 204

    webhook_response = await client.post(
        f"/api/v1/integrations/alice/webhook?token={token}",
        json=_alice_request("create task: water the plants"),
    )
    assert "linked" in webhook_response.json()["response"]["text"].lower()

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(owner))
    assert tasks_response.json()["items"] == []


@pytest.mark.asyncio
async def test_reissuing_a_token_invalidates_the_previous_one(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    first = (
        await client.post("/api/v1/integrations/alice/token", headers=_auth_headers(owner))
    ).json()["token"]
    second = (
        await client.post("/api/v1/integrations/alice/token", headers=_auth_headers(owner))
    ).json()["token"]
    assert first != second

    old_token_response = await client.post(
        f"/api/v1/integrations/alice/webhook?token={first}",
        json=_alice_request("create task: water the plants"),
    )
    assert "linked" in old_token_response.json()["response"]["text"].lower()

    new_token_response = await client.post(
        f"/api/v1/integrations/alice/webhook?token={second}",
        json=_alice_request("create task: water the plants"),
    )
    assert "water the plants" in new_token_response.json()["response"]["text"].lower()


@pytest.mark.asyncio
async def test_webhook_unrecognized_utterance_does_not_create_a_task(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    token = (
        await client.post("/api/v1/integrations/alice/token", headers=_auth_headers(owner))
    ).json()["token"]

    await client.post(
        f"/api/v1/integrations/alice/webhook?token={token}",
        json=_alice_request("what's the weather like"),
    )

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(owner))
    assert tasks_response.json()["items"] == []

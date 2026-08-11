from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


@pytest.mark.asyncio
async def test_list_members_initially_has_only_owner(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.get("/api/v1/users", headers=_auth_headers(owner))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["email"] == owner["user"]["email"]
    assert body[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_owner_can_invite_member(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/users",
        json={
            "email": "lena@example.com",
            "display_name": "Lena",
            "password": "correct-horse-battery-staple",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "lena@example.com"
    assert body["role"] == "member"
    assert body["tenant_id"] == owner["user"]["tenant_id"]

    members_response = await client.get("/api/v1/users", headers=_auth_headers(owner))
    emails = {member["email"] for member in members_response.json()}
    assert emails == {owner["user"]["email"], "lena@example.com"}


@pytest.mark.asyncio
async def test_invited_member_can_log_in_and_see_shared_tasks(
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

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login_response.status_code == 200
    lena = login_response.json()

    await client.post("/api/v1/tasks", json={"title": "Shared chore"}, headers=_auth_headers(owner))

    tasks_response = await client.get("/api/v1/tasks", headers=_auth_headers(lena))
    assert tasks_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_member_cannot_invite_other_members(
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
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    lena = login_response.json()

    response = await client.post(
        "/api/v1/users",
        json={
            "email": "someone-else@example.com",
            "display_name": "Someone",
            "password": "correct-horse-battery-staple",
        },
        headers=_auth_headers(lena),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_invite_with_duplicate_email_fails(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/users",
        json={
            "email": owner["user"]["email"],
            "display_name": "Duplicate",
            "password": "correct-horse-battery-staple",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_list_members_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_create_invite_link(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post("/api/v1/users/invites", headers=_auth_headers(owner))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token"]
    assert body["expires_at"]


@pytest.mark.asyncio
async def test_member_cannot_create_invite_link(
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
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    lena = login_response.json()

    response = await client.post("/api/v1/users/invites", headers=_auth_headers(lena))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invite_link_preview_shows_household_name(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    invite = (await client.post("/api/v1/users/invites", headers=_auth_headers(owner))).json()

    response = await client.get(f"/api/v1/users/invites/{invite['token']}")

    assert response.status_code == 200, response.text
    assert response.json()["household_name"] == "Test Household"


@pytest.mark.asyncio
async def test_invalid_invite_token_preview_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/invites/not-a-real-token")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_INVITE"


@pytest.mark.asyncio
async def test_redeeming_invite_link_creates_member_and_logs_in(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    invite = (await client.post("/api/v1/users/invites", headers=_auth_headers(owner))).json()

    response = await client.post(
        f"/api/v1/auth/invites/{invite['token']}/redeem",
        json={
            "email": "lena@example.com",
            "display_name": "Lena",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "lena@example.com"
    assert body["user"]["role"] == "member"
    assert body["user"]["tenant_id"] == owner["user"]["tenant_id"]
    assert body["access_token"]

    members_response = await client.get("/api/v1/users", headers=_auth_headers(owner))
    emails = {member["email"] for member in members_response.json()}
    assert emails == {owner["user"]["email"], "lena@example.com"}


@pytest.mark.asyncio
async def test_invite_link_cannot_be_redeemed_twice(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    invite = (await client.post("/api/v1/users/invites", headers=_auth_headers(owner))).json()
    await client.post(
        f"/api/v1/auth/invites/{invite['token']}/redeem",
        json={
            "email": "lena@example.com",
            "display_name": "Lena",
            "password": "correct-horse-battery-staple",
        },
    )

    response = await client.post(
        f"/api/v1/auth/invites/{invite['token']}/redeem",
        json={
            "email": "someone-else@example.com",
            "display_name": "Someone",
            "password": "correct-horse-battery-staple",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_INVITE"

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "household_name": "Pasha & Lena",
    "display_name": "Pasha",
    "email": "pasha@example.com",
    "password": "correct-horse-battery-staple",
}


async def _register(client: AsyncClient, **overrides: str) -> dict:
    payload = {**REGISTER_PAYLOAD, **overrides}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_register_creates_household_owner(client: AsyncClient) -> None:
    body = await _register(client)

    assert body["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert body["user"]["role"] == "owner"
    assert body["access_token"]
    assert "refresh_token" in client.cookies
    assert "csrf_token" in client.cookies


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await _register(client)

    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_login_with_correct_password_succeeds(client: AsyncClient) -> None:
    await _register(client)
    client.cookies.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == REGISTER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_login_with_wrong_password_fails(client: AsyncClient) -> None:
    await _register(client)
    client.cookies.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_throttles_after_repeated_failures(client: AsyncClient) -> None:
    await _register(client)
    client.cookies.clear()

    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
        )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_LOGIN_ATTEMPTS"


@pytest.mark.asyncio
async def test_me_requires_bearer_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_me_returns_current_user_with_valid_token(client: AsyncClient) -> None:
    body = await _register(client)
    access_token = body["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_PAYLOAD["email"]


@pytest.mark.asyncio
async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_old_one_stops_working(client: AsyncClient) -> None:
    await _register(client)
    old_refresh_cookie = client.cookies["refresh_token"]
    old_csrf_cookie = client.cookies["csrf_token"]

    response = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": old_csrf_cookie})

    assert response.status_code == 200
    assert client.cookies["refresh_token"] != old_refresh_cookie

    # The rotated-out refresh token must no longer work.
    client.cookies.set("refresh_token", old_refresh_cookie)
    client.cookies.set("csrf_token", old_csrf_cookie)
    reuse_response = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": old_csrf_cookie}
    )

    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_refresh_without_csrf_header_is_rejected(client: AsyncClient) -> None:
    await _register(client)

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_TOKEN_MISMATCH"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await _register(client)
    csrf_cookie = client.cookies["csrf_token"]

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf_cookie}
    )
    assert refresh_response.status_code in (401, 403)

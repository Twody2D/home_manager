from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from home_manager.db.session import get_engine

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


def _subscription_payload(endpoint: str) -> dict:
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": "test-p256dh-key", "auth": "test-auth-secret"},
    }


async def _count_subscriptions(endpoint: str) -> int:
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM push_subscriptions WHERE endpoint = :endpoint"),
            {"endpoint": endpoint},
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_vapid_public_key_disabled_by_default(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.get(
        "/api/v1/notifications/vapid-public-key", headers=_auth_headers(owner)
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NOTIFICATIONS_DISABLED"


@pytest.mark.asyncio
async def test_subscriptions_require_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/notifications/subscriptions", json=_subscription_payload("https://example.com/x")
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    endpoint = "https://push.example.com/subscription/abc"

    subscribe_response = await client.post(
        "/api/v1/notifications/subscriptions",
        json=_subscription_payload(endpoint),
        headers=_auth_headers(owner),
    )
    assert subscribe_response.status_code == 204
    assert await _count_subscriptions(endpoint) == 1

    unsubscribe_response = await client.request(
        "DELETE",
        f"/api/v1/notifications/subscriptions?endpoint={endpoint}",
        headers=_auth_headers(owner),
    )
    assert unsubscribe_response.status_code == 204
    assert await _count_subscriptions(endpoint) == 0


@pytest.mark.asyncio
async def test_resubscribing_same_endpoint_does_not_duplicate(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    endpoint = "https://push.example.com/subscription/repeat"

    for _ in range(2):
        response = await client.post(
            "/api/v1/notifications/subscriptions",
            json=_subscription_payload(endpoint),
            headers=_auth_headers(owner),
        )
        assert response.status_code == 204

    assert await _count_subscriptions(endpoint) == 1


@pytest.mark.asyncio
async def test_unsubscribe_unknown_endpoint_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.request(
        "DELETE",
        "/api/v1/notifications/subscriptions?endpoint=https://nope.example.com",
        headers=_auth_headers(owner),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBSCRIPTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_test_notification_returns_zero_when_push_is_disabled(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post("/api/v1/notifications/test", headers=_auth_headers(owner))

    assert response.status_code == 200
    assert response.json()["sent"] == 0


@pytest.mark.asyncio
async def test_assigning_task_to_another_member_still_succeeds_without_push_configured(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    invite_response = await client.post(
        "/api/v1/users",
        json={
            "email": "lena@example.com",
            "display_name": "Lena",
            "password": "correct-horse-battery-staple",
        },
        headers=_auth_headers(owner),
    )
    lena = invite_response.json()

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Take out the trash", "assigned_to": lena["id"]},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    assert response.json()["assigned_to"] == lena["id"]

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


# --- Incomes ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_income_defaults_user_to_creator(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "3000.00", "payment_day": 25},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == owner["user"]["id"]
    assert body["amount"] == "3000.00"
    assert body["payment_day"] == 25


@pytest.mark.asyncio
async def test_can_create_income_for_household_partner(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    partner = await _invite_member(client, owner)

    response = await client.post(
        "/api/v1/finance/incomes",
        json={
            "user_id": partner["id"],
            "label": "Salary",
            "amount": "2500.00",
            "payment_day": 25,
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == partner["id"]


@pytest.mark.asyncio
async def test_cannot_create_income_for_user_outside_household(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    stranger = await register_household(client, email="stranger@example.com")

    response = await client.post(
        "/api/v1/finance/incomes",
        json={
            "user_id": stranger["user"]["id"],
            "label": "Salary",
            "amount": "1000.00",
            "payment_day": 1,
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INCOME_OWNER"


@pytest.mark.asyncio
async def test_income_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    create_response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "3000.00", "payment_day": 25},
        headers=_auth_headers(owner_a),
    )
    income_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/finance/incomes/{income_id}", headers=_auth_headers(owner_b)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_household_members_can_edit_each_others_income(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    await _invite_member(client, owner)

    create_response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "3000.00", "payment_day": 25},
        headers=_auth_headers(owner),
    )
    income_id = create_response.json()["id"]

    # Invited members are created (not logged in) by POST /users — log in
    # separately to get their own token.
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lena@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login_response.status_code == 200, login_response.text
    partner_token = login_response.json()

    response = await client.patch(
        f"/api/v1/finance/incomes/{income_id}",
        json={"amount": "3200.00"},
        headers=_auth_headers(partner_token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["amount"] == "3200.00"


@pytest.mark.asyncio
async def test_income_rejects_zero_or_negative_amount(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "0", "payment_day": 25},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_income_rejects_invalid_payment_day(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "3000.00", "payment_day": 32},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_income(client: AsyncClient, register_household: RegisterHousehold) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/finance/incomes",
        json={"label": "Salary", "amount": "3000.00", "payment_day": 25},
        headers=_auth_headers(owner),
    )
    income_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/finance/incomes/{income_id}", headers=_auth_headers(owner)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/finance/incomes/{income_id}", headers=_auth_headers(owner)
    )
    assert get_response.status_code == 404


# --- Subscriptions -----------------------------------------------------------


@pytest.mark.asyncio
async def test_create_subscription(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Netflix"
    assert body["active"] is True
    assert body["owner_user_id"] is None


@pytest.mark.asyncio
async def test_create_subscription_with_owner(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={
            "name": "Spotify",
            "amount": "11.99",
            "payment_day": 3,
            "owner_user_id": owner["user"]["id"],
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    assert response.json()["owner_user_id"] == owner["user"]["id"]


@pytest.mark.asyncio
async def test_cannot_create_subscription_with_owner_outside_household(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    stranger = await register_household(client, email="stranger@example.com")

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={
            "name": "Spotify",
            "amount": "11.99",
            "payment_day": 3,
            "owner_user_id": stranger["user"]["id"],
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SUBSCRIPTION_OWNER"


@pytest.mark.asyncio
async def test_subscription_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    create_response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner_a),
    )
    subscription_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/finance/subscriptions/{subscription_id}", headers=_auth_headers(owner_b)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_subscriptions_active_only_filters_inactive(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    active = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner),
    )
    inactive = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Old gym", "amount": "30.00", "payment_day": 1},
        headers=_auth_headers(owner),
    )
    await client.patch(
        f"/api/v1/finance/subscriptions/{inactive.json()['id']}",
        json={"active": False},
        headers=_auth_headers(owner),
    )

    response = await client.get(
        "/api/v1/finance/subscriptions?active_only=true", headers=_auth_headers(owner)
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert active.json()["id"] in ids
    assert inactive.json()["id"] not in ids


@pytest.mark.asyncio
async def test_create_yearly_subscription_requires_payment_month(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Domain renewal", "amount": "12.00", "payment_day": 5, "cadence": "yearly"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_monthly_subscription_rejects_payment_month(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={
            "name": "Netflix",
            "amount": "15.99",
            "payment_day": 5,
            "cadence": "monthly",
            "payment_month": 3,
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_yearly_subscription(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/finance/subscriptions",
        json={
            "name": "Domain renewal",
            "amount": "12.00",
            "payment_day": 5,
            "cadence": "yearly",
            "payment_month": 3,
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cadence"] == "yearly"
    assert body["payment_month"] == 3


@pytest.mark.asyncio
async def test_update_subscription_fields(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner),
    )
    subscription_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/finance/subscriptions/{subscription_id}",
        json={"name": "Netflix Premium", "amount": "19.99", "payment_day": 20},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Netflix Premium"
    assert body["amount"] == "19.99"
    assert body["payment_day"] == 20


@pytest.mark.asyncio
async def test_update_subscription_to_yearly_requires_payment_month(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner),
    )
    subscription_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/finance/subscriptions/{subscription_id}",
        json={"cadence": "yearly"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SUBSCRIPTION_CADENCE"


@pytest.mark.asyncio
async def test_delete_subscription(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/finance/subscriptions",
        json={"name": "Netflix", "amount": "15.99", "payment_day": 15},
        headers=_auth_headers(owner),
    )
    subscription_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/finance/subscriptions/{subscription_id}", headers=_auth_headers(owner)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/finance/subscriptions/{subscription_id}", headers=_auth_headers(owner)
    )
    assert get_response.status_code == 404


# --- Rename own profile (PATCH /users/me) -----------------------------------


@pytest.mark.asyncio
async def test_update_my_display_name(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.patch(
        "/api/v1/users/me", json={"display_name": "Паша"}, headers=_auth_headers(owner)
    )

    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Паша"

    list_response = await client.get("/api/v1/users", headers=_auth_headers(owner))
    assert list_response.json()[0]["display_name"] == "Паша"

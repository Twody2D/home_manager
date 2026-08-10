from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


@pytest.mark.asyncio
async def test_create_task_defaults(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/tasks", json={"title": "Buy groceries"}, headers=_auth_headers(owner)
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Buy groceries"
    assert body["status"] == "pending"
    assert body["priority"] == "medium"
    assert body["created_by"] == owner["user"]["id"]
    assert body["tenant_id"] == owner["user"]["tenant_id"]
    assert body["assigned_to"] is None
    assert body["completed_at"] is None


@pytest.mark.asyncio
async def test_create_task_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tasks", json={"title": "Buy groceries"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_preferred_window(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Impossible window",
            "preferred_start": "2026-01-01T10:00:00Z",
            "preferred_end": "2026-01-01T09:00:00Z",
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_rejects_assignee_outside_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Sneaky assignment", "assigned_to": owner_b["user"]["id"]},
        headers=_auth_headers(owner_a),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ASSIGNEE"


@pytest.mark.asyncio
async def test_list_tasks_is_scoped_to_own_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    await client.post("/api/v1/tasks", json={"title": "A's task"}, headers=_auth_headers(owner_a))
    await client.post("/api/v1/tasks", json={"title": "B's task"}, headers=_auth_headers(owner_b))

    response = await client.get("/api/v1/tasks", headers=_auth_headers(owner_a))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [t["title"] for t in body["items"]] == ["A's task"]


@pytest.mark.asyncio
async def test_get_task_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    create_response = await client.post(
        "/api/v1/tasks", json={"title": "A's task"}, headers=_auth_headers(owner_a)
    )
    task_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth_headers(owner_b))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_task_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    create_response = await client.post(
        "/api/v1/tasks", json={"title": "A's task"}, headers=_auth_headers(owner_a)
    )
    task_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"title": "Hijacked"}, headers=_auth_headers(owner_b)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task_status_sets_completed_at(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/tasks", json={"title": "Do the dishes"}, headers=_auth_headers(owner)
    )
    task_id = create_response.json()["id"]

    completed = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"status": "completed"}, headers=_auth_headers(owner)
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    reopened = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"status": "pending"}, headers=_auth_headers(owner)
    )
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, register_household: RegisterHousehold) -> None:
    owner = await register_household(client)
    create_response = await client.post(
        "/api/v1/tasks", json={"title": "Throw out trash"}, headers=_auth_headers(owner)
    )
    task_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/tasks/{task_id}", headers=_auth_headers(owner))
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth_headers(owner))
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status_and_paginates(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    for i in range(3):
        await client.post("/api/v1/tasks", json={"title": f"Task {i}"}, headers=headers)
    completed_response = await client.post(
        "/api/v1/tasks", json={"title": "Already done"}, headers=headers
    )
    await client.patch(
        f"/api/v1/tasks/{completed_response.json()['id']}",
        json={"status": "completed"},
        headers=headers,
    )

    pending_response = await client.get("/api/v1/tasks?status=pending", headers=headers)
    assert pending_response.json()["total"] == 3

    completed_list_response = await client.get("/api/v1/tasks?status=completed", headers=headers)
    assert completed_list_response.json()["total"] == 1

    paged_response = await client.get("/api/v1/tasks?limit=2&offset=0", headers=headers)
    paged_body = paged_response.json()
    assert paged_body["total"] == 4
    assert len(paged_body["items"]) == 2

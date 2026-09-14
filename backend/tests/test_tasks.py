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
async def test_create_task_with_personal_budget(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "New shoes",
            "budget_amount": "3500.00",
            "budget_owner_user_id": owner["user"]["id"],
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["budget_amount"] == "3500.00"
    assert body["budget_owner_user_id"] == owner["user"]["id"]


@pytest.mark.asyncio
async def test_create_task_with_shared_budget_defaults_owner_to_null(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Grocery run", "budget_amount": "2000.00"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["budget_amount"] == "2000.00"
    assert body["budget_owner_user_id"] is None


@pytest.mark.asyncio
async def test_create_task_rejects_zero_budget(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Free task", "budget_amount": "0"},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_rejects_budget_owner_outside_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Sneaky budget",
            "budget_amount": "100.00",
            "budget_owner_user_id": owner_b["user"]["id"],
        },
        headers=_auth_headers(owner_a),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BUDGET_OWNER"


@pytest.mark.asyncio
async def test_update_task_budget(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    created = await client.post(
        "/api/v1/tasks", json={"title": "Repaint fence"}, headers=_auth_headers(owner)
    )
    task_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"budget_amount": "8000.00", "budget_owner_user_id": owner["user"]["id"]},
        headers=_auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["budget_amount"] == "8000.00"
    assert body["budget_owner_user_id"] == owner["user"]["id"]


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


@pytest.mark.asyncio
async def test_create_and_list_task_lists(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    create_response = await client.post(
        "/api/v1/task-lists", json={"name": "Покупки"}, headers=headers
    )
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["name"] == "Покупки"

    list_response = await client.get("/api/v1/task-lists", headers=headers)
    assert list_response.status_code == 200
    names = [item["name"] for item in list_response.json()["items"]]
    assert names == ["Покупки"]


@pytest.mark.asyncio
async def test_task_lists_are_scoped_to_own_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    await client.post(
        "/api/v1/task-lists", json={"name": "A's list"}, headers=_auth_headers(owner_a)
    )

    response = await client.get("/api/v1/task-lists", headers=_auth_headers(owner_b))
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_rename_and_delete_task_list(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    created = await client.post("/api/v1/task-lists", json={"name": "Треки"}, headers=headers)
    list_id = created.json()["id"]

    rename_response = await client.patch(
        f"/api/v1/task-lists/{list_id}", json={"name": "Музыка"}, headers=headers
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "Музыка"

    delete_response = await client.delete(f"/api/v1/task-lists/{list_id}", headers=headers)
    assert delete_response.status_code == 204

    list_response = await client.get("/api/v1/task-lists", headers=headers)
    assert list_response.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_task_list_moves_tasks_to_my_tasks(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    task_list = await client.post("/api/v1/task-lists", json={"name": "Покупки"}, headers=headers)
    list_id = task_list.json()["id"]
    task = await client.post(
        "/api/v1/tasks", json={"title": "Молоко", "list_id": list_id}, headers=headers
    )
    assert task.json()["list_id"] == list_id

    await client.delete(f"/api/v1/task-lists/{list_id}", headers=headers)

    refreshed = await client.get(f"/api/v1/tasks/{task.json()['id']}", headers=headers)
    assert refreshed.json()["list_id"] is None


@pytest.mark.asyncio
async def test_create_task_rejects_list_outside_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    task_list = await client.post(
        "/api/v1/task-lists", json={"name": "A's list"}, headers=_auth_headers(owner_a)
    )

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Sneaky", "list_id": task_list.json()["id"]},
        headers=_auth_headers(owner_b),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TASK_LIST"


@pytest.mark.asyncio
async def test_create_subtask_inherits_parent_list(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    task_list = await client.post("/api/v1/task-lists", json={"name": "Покупки"}, headers=headers)
    list_id = task_list.json()["id"]
    other_list = await client.post(
        "/api/v1/task-lists", json={"name": "Другая папка"}, headers=headers
    )
    parent = await client.post(
        "/api/v1/tasks", json={"title": "Продукты", "list_id": list_id}, headers=headers
    )
    parent_id = parent.json()["id"]

    # Passing a different list_id alongside parent_task_id is ignored — a
    # subtask always inherits its parent's list.
    subtask = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Молоко",
            "parent_task_id": parent_id,
            "list_id": other_list.json()["id"],
        },
        headers=headers,
    )
    assert subtask.status_code == 201, subtask.text
    assert subtask.json()["list_id"] == list_id
    assert subtask.json()["parent_task_id"] == parent_id


@pytest.mark.asyncio
async def test_create_subtask_rejects_nested_parent(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    child = await client.post(
        "/api/v1/tasks",
        json={"title": "Child", "parent_task_id": parent.json()["id"]},
        headers=headers,
    )

    grandchild = await client.post(
        "/api/v1/tasks",
        json={"title": "Grandchild", "parent_task_id": child.json()["id"]},
        headers=headers,
    )
    assert grandchild.status_code == 422
    assert grandchild.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_create_subtask_rejects_parent_outside_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    parent = await client.post(
        "/api/v1/tasks", json={"title": "A's task"}, headers=_auth_headers(owner_a)
    )

    response = await client.post(
        "/api/v1/tasks",
        json={"title": "Sneaky", "parent_task_id": parent.json()["id"]},
        headers=_auth_headers(owner_b),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_cannot_convert_task_with_children_into_a_subtask(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": parent_id}, headers=headers
    )
    other = await client.post("/api/v1/tasks", json={"title": "Other"}, headers=headers)

    response = await client.patch(
        f"/api/v1/tasks/{parent_id}",
        json={"parent_task_id": other.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_task_cannot_be_its_own_parent(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    task = await client.post("/api/v1/tasks", json={"title": "Solo"}, headers=headers)

    response = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"parent_task_id": task.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_update_task_moves_between_lists(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    list_a = await client.post("/api/v1/task-lists", json={"name": "A"}, headers=headers)
    list_b = await client.post("/api/v1/task-lists", json={"name": "B"}, headers=headers)
    task = await client.post(
        "/api/v1/tasks", json={"title": "Movable", "list_id": list_a.json()["id"]}, headers=headers
    )

    response = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"list_id": list_b.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["list_id"] == list_b.json()["id"]

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
async def test_deleting_a_task_cascades_to_its_whole_subtask_tree(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    child = await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": parent_id}, headers=headers
    )
    child_id = child.json()["id"]
    grandchild = await client.post(
        "/api/v1/tasks", json={"title": "Grandchild", "parent_task_id": child_id}, headers=headers
    )
    grandchild_id = grandchild.json()["id"]

    delete_response = await client.delete(f"/api/v1/tasks/{parent_id}", headers=headers)
    assert delete_response.status_code == 204

    assert (await client.get(f"/api/v1/tasks/{child_id}", headers=headers)).status_code == 404
    assert (await client.get(f"/api/v1/tasks/{grandchild_id}", headers=headers)).status_code == 404


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
async def test_task_list_owner_defaults_to_shared_and_can_be_reassigned(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    owner_id = owner["user"]["id"]

    shared = await client.post("/api/v1/task-lists", json={"name": "Общие"}, headers=headers)
    assert shared.status_code == 201, shared.text
    assert shared.json()["owner_user_id"] is None

    mine = await client.post(
        "/api/v1/task-lists", json={"name": "Треки", "owner_user_id": owner_id}, headers=headers
    )
    assert mine.json()["owner_user_id"] == owner_id

    # Renaming on its own leaves the section alone...
    renamed = await client.patch(
        f"/api/v1/task-lists/{mine.json()['id']}", json={"name": "Музыка"}, headers=headers
    )
    assert renamed.json()["name"] == "Музыка"
    assert renamed.json()["owner_user_id"] == owner_id

    # ...and an explicit null moves the folder back to the shared section.
    moved = await client.patch(
        f"/api/v1/task-lists/{mine.json()['id']}", json={"owner_user_id": None}, headers=headers
    )
    assert moved.json()["owner_user_id"] is None
    assert moved.json()["name"] == "Музыка"


@pytest.mark.asyncio
async def test_task_list_owner_must_be_in_same_household(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    response = await client.post(
        "/api/v1/task-lists",
        json={"name": "Чужая", "owner_user_id": owner_b["user"]["id"]},
        headers=_auth_headers(owner_a),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TASK_LIST_OWNER"


@pytest.mark.asyncio
async def test_reorder_task_lists(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    a = await client.post("/api/v1/task-lists", json={"name": "A"}, headers=headers)
    b = await client.post("/api/v1/task-lists", json={"name": "B"}, headers=headers)
    c = await client.post("/api/v1/task-lists", json={"name": "C"}, headers=headers)
    a_id, b_id, c_id = a.json()["id"], b.json()["id"], c.json()["id"]

    response = await client.patch(
        "/api/v1/task-lists/reorder",
        json={"ordered_ids": [c_id, a_id, b_id]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["id"] for item in body] == [c_id, a_id, b_id]
    assert [item["order_index"] for item in body] == [0, 1, 2]

    listed = await client.get("/api/v1/task-lists", headers=headers)
    assert [item["id"] for item in listed.json()["items"]] == [c_id, a_id, b_id]


@pytest.mark.asyncio
async def test_reorder_task_lists_rejects_partial_id_set(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    a = await client.post("/api/v1/task-lists", json={"name": "A"}, headers=headers)
    await client.post("/api/v1/task-lists", json={"name": "B"}, headers=headers)

    response = await client.patch(
        "/api/v1/task-lists/reorder",
        json={"ordered_ids": [a.json()["id"]]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_LIST_REORDER"


@pytest.mark.asyncio
async def test_reorder_task_lists_rejects_list_from_other_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    a1 = await client.post(
        "/api/v1/task-lists", json={"name": "A1"}, headers=_auth_headers(owner_a)
    )
    b1 = await client.post(
        "/api/v1/task-lists", json={"name": "B1"}, headers=_auth_headers(owner_b)
    )

    response = await client.patch(
        "/api/v1/task-lists/reorder",
        json={"ordered_ids": [a1.json()["id"], b1.json()["id"]]},
        headers=_auth_headers(owner_a),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_LIST_REORDER"


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
async def test_create_sub_subtask_under_a_subtask(
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
    assert grandchild.status_code == 201, grandchild.text
    assert grandchild.json()["parent_task_id"] == child.json()["id"]
    # A sub-subtask inherits the top-level task's list, transitively through
    # its immediate (subtask) parent.
    assert grandchild.json()["list_id"] == parent.json()["list_id"]


@pytest.mark.asyncio
async def test_create_subtask_rejects_fifth_level_nesting(
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
    great_grandchild = await client.post(
        "/api/v1/tasks",
        json={"title": "Great-grandchild", "parent_task_id": grandchild.json()["id"]},
        headers=headers,
    )
    assert great_grandchild.status_code == 201, great_grandchild.text

    great_great_grandchild = await client.post(
        "/api/v1/tasks",
        json={"title": "Great-great-grandchild", "parent_task_id": great_grandchild.json()["id"]},
        headers=headers,
    )
    assert great_great_grandchild.status_code == 422
    assert great_great_grandchild.json()["error"]["code"] == "INVALID_PARENT_TASK"


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
async def test_can_convert_task_with_children_into_an_ordinary_subtask(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    # A task with children can become an ordinary (top-level-parented)
    # subtask — its children simply become sub-subtasks, still within the
    # four-level cap.
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    child = await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": parent_id}, headers=headers
    )
    other = await client.post("/api/v1/tasks", json={"title": "Other"}, headers=headers)

    response = await client.patch(
        f"/api/v1/tasks/{parent_id}",
        json={"parent_task_id": other.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["parent_task_id"] == other.json()["id"]

    refreshed_child = await client.get(f"/api/v1/tasks/{child.json()['id']}", headers=headers)
    assert refreshed_child.json()["parent_task_id"] == parent_id


@pytest.mark.asyncio
async def test_can_convert_task_with_children_into_a_sub_subtask(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    # Converting a task with children into a SUB-subtask (parented under an
    # existing subtask) pushes its children to a fourth level, which now
    # fits within the four-level cap.
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    child = await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": parent_id}, headers=headers
    )
    top = await client.post("/api/v1/tasks", json={"title": "Top"}, headers=headers)
    existing_subtask = await client.post(
        "/api/v1/tasks",
        json={"title": "Existing subtask", "parent_task_id": top.json()["id"]},
        headers=headers,
    )

    response = await client.patch(
        f"/api/v1/tasks/{parent_id}",
        json={"parent_task_id": existing_subtask.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    refreshed_child = await client.get(f"/api/v1/tasks/{child.json()['id']}", headers=headers)
    assert refreshed_child.json()["parent_task_id"] == parent_id


@pytest.mark.asyncio
async def test_cannot_convert_task_with_children_into_a_sub_sub_subtask(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    # Converting a task with children into a SUB-SUB-subtask (parented under
    # an existing sub-subtask) would push its children to a fifth level, so
    # it's still rejected.
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": parent_id}, headers=headers
    )
    top = await client.post("/api/v1/tasks", json={"title": "Top"}, headers=headers)
    sub = await client.post(
        "/api/v1/tasks", json={"title": "Sub", "parent_task_id": top.json()["id"]}, headers=headers
    )
    sub_sub = await client.post(
        "/api/v1/tasks",
        json={"title": "SubSub", "parent_task_id": sub.json()["id"]},
        headers=headers,
    )

    response = await client.patch(
        f"/api/v1/tasks/{parent_id}",
        json={"parent_task_id": sub_sub.json()["id"]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_cannot_nest_task_under_its_own_descendant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    top = await client.post("/api/v1/tasks", json={"title": "Top"}, headers=headers)
    top_id = top.json()["id"]
    child = await client.post(
        "/api/v1/tasks", json={"title": "Child", "parent_task_id": top_id}, headers=headers
    )

    response = await client.patch(
        f"/api/v1/tasks/{top_id}",
        json={"parent_task_id": child.json()["id"]},
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


@pytest.mark.asyncio
async def test_new_tasks_get_increasing_order_index(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    first = await client.post("/api/v1/tasks", json={"title": "First"}, headers=headers)
    second = await client.post("/api/v1/tasks", json={"title": "Second"}, headers=headers)
    third = await client.post("/api/v1/tasks", json={"title": "Third"}, headers=headers)

    assert first.json()["order_index"] == 0
    assert second.json()["order_index"] == 1
    assert third.json()["order_index"] == 2


@pytest.mark.asyncio
async def test_reorder_top_level_tasks(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    a = await client.post("/api/v1/tasks", json={"title": "A"}, headers=headers)
    b = await client.post("/api/v1/tasks", json={"title": "B"}, headers=headers)
    c = await client.post("/api/v1/tasks", json={"title": "C"}, headers=headers)
    a_id, b_id, c_id = a.json()["id"], b.json()["id"], c.json()["id"]

    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={"list_id": None, "parent_task_id": None, "ordered_ids": [c_id, a_id, b_id]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["id"] for item in body] == [c_id, a_id, b_id]
    assert [item["order_index"] for item in body] == [0, 1, 2]

    listed = await client.get("/api/v1/tasks", headers=headers)
    by_id = {item["id"]: item["order_index"] for item in listed.json()["items"]}
    assert by_id == {c_id: 0, a_id: 1, b_id: 2}


@pytest.mark.asyncio
async def test_reorder_subtasks_independently_of_parent_group(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    parent = await client.post("/api/v1/tasks", json={"title": "Parent"}, headers=headers)
    parent_id = parent.json()["id"]
    child_a = await client.post(
        "/api/v1/tasks", json={"title": "Child A", "parent_task_id": parent_id}, headers=headers
    )
    child_b = await client.post(
        "/api/v1/tasks", json={"title": "Child B", "parent_task_id": parent_id}, headers=headers
    )

    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={
            "list_id": None,
            "parent_task_id": parent_id,
            "ordered_ids": [child_b.json()["id"], child_a.json()["id"]],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [
        child_b.json()["id"],
        child_a.json()["id"],
    ]


@pytest.mark.asyncio
async def test_reorder_sub_subtasks(
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
    child_id = child.json()["id"]
    grand_a = await client.post(
        "/api/v1/tasks", json={"title": "Grand A", "parent_task_id": child_id}, headers=headers
    )
    grand_b = await client.post(
        "/api/v1/tasks", json={"title": "Grand B", "parent_task_id": child_id}, headers=headers
    )

    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={
            "list_id": None,
            "parent_task_id": child_id,
            "ordered_ids": [grand_b.json()["id"], grand_a.json()["id"]],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [
        grand_b.json()["id"],
        grand_a.json()["id"],
    ]


@pytest.mark.asyncio
async def test_reorder_rejects_partial_id_set(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    a = await client.post("/api/v1/tasks", json={"title": "A"}, headers=headers)
    await client.post("/api/v1/tasks", json={"title": "B"}, headers=headers)

    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={"list_id": None, "parent_task_id": None, "ordered_ids": [a.json()["id"]]},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REORDER"


@pytest.mark.asyncio
async def test_reorder_rejects_task_from_other_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    a1 = await client.post("/api/v1/tasks", json={"title": "A1"}, headers=_auth_headers(owner_a))
    a2 = await client.post("/api/v1/tasks", json={"title": "A2"}, headers=_auth_headers(owner_a))
    b1 = await client.post("/api/v1/tasks", json={"title": "B1"}, headers=_auth_headers(owner_b))

    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={
            "list_id": None,
            "parent_task_id": None,
            "ordered_ids": [a1.json()["id"], b1.json()["id"]],
        },
        headers=_auth_headers(owner_a),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REORDER"

    # Sanity: A's own two tasks still reorder fine, proving the rejection
    # above was specifically about the foreign id, not a broken endpoint.
    ok_response = await client.patch(
        "/api/v1/tasks/reorder",
        json={
            "list_id": None,
            "parent_task_id": None,
            "ordered_ids": [a2.json()["id"], a1.json()["id"]],
        },
        headers=_auth_headers(owner_a),
    )
    assert ok_response.status_code == 200, ok_response.text


@pytest.mark.asyncio
async def test_reorder_scoped_to_correct_list(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    list_a = await client.post("/api/v1/task-lists", json={"name": "A"}, headers=headers)
    list_id = list_a.json()["id"]
    in_list = await client.post(
        "/api/v1/tasks", json={"title": "In list", "list_id": list_id}, headers=headers
    )
    in_my_tasks = await client.post("/api/v1/tasks", json={"title": "My tasks"}, headers=headers)

    # Trying to reorder a "My Tasks" task under list_id's group is rejected
    # because it's not actually a member of that sibling group.
    response = await client.patch(
        "/api/v1/tasks/reorder",
        json={
            "list_id": list_id,
            "parent_task_id": None,
            "ordered_ids": [in_list.json()["id"], in_my_tasks.json()["id"]],
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REORDER"

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

RegisterHousehold = Callable[..., Awaitable[dict]]


def _auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}


VIDEO_IDEAS = [
    {"text": "VST плагин с пердежом"},
    {
        "text": "Все форматы звука: объясняю за 9 минут",
        "children": [{"text": "Собрать примеры"}, {"text": "Записать закадр"}],
    },
]


@pytest.mark.asyncio
async def test_create_and_list_notes(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    created = await client.post(
        "/api/v1/notes", json={"title": "Идеи для видео", "items": VIDEO_IDEAS}, headers=headers
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["title"] == "Идеи для видео"
    assert body["items"][1]["children"][0]["text"] == "Собрать примеры"
    assert body["created_by"] == owner["user"]["id"]

    listed = await client.get("/api/v1/notes", headers=headers)
    assert [note["title"] for note in listed.json()["items"]] == ["Идеи для видео"]


@pytest.mark.asyncio
async def test_notes_are_scoped_to_own_tenant(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")

    await client.post("/api/v1/notes", json={"title": "A's note"}, headers=_auth_headers(owner_a))

    assert (await client.get("/api/v1/notes", headers=_auth_headers(owner_b))).json()["items"] == []


@pytest.mark.asyncio
async def test_update_and_delete_note(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    created = await client.post("/api/v1/notes", json={"title": "Идеи"}, headers=headers)
    note_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/notes/{note_id}",
        json={"title": "Идеи для видео", "items": VIDEO_IDEAS},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Идеи для видео"
    assert len(updated.json()["items"]) == 2

    assert (await client.delete(f"/api/v1/notes/{note_id}", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/notes", headers=headers)).json()["items"] == []


@pytest.mark.asyncio
async def test_convert_note_item_into_a_task_with_subtasks(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    task_list = await client.post("/api/v1/task-lists", json={"name": "Видео"}, headers=headers)
    list_id = task_list.json()["id"]
    note = await client.post(
        "/api/v1/notes", json={"title": "Идеи для видео", "items": VIDEO_IDEAS}, headers=headers
    )
    note_id = note.json()["id"]

    converted = await client.post(
        f"/api/v1/notes/{note_id}/convert",
        json={"path": [1], "list_id": list_id},
        headers=headers,
    )
    assert converted.status_code == 201, converted.text
    root = converted.json()
    assert root["title"] == "Все форматы звука: объясняю за 9 минут"
    assert root["list_id"] == list_id
    assert root["assigned_to"] == owner["user"]["id"]

    tasks = (await client.get("/api/v1/tasks?limit=1000", headers=headers)).json()["items"]
    by_title = {task["title"]: task for task in tasks}
    assert len(tasks) == 3
    assert by_title["Собрать примеры"]["parent_task_id"] == root["id"]
    assert by_title["Записать закадр"]["parent_task_id"] == root["id"]

    # Kept by default — the idea list is also a record of what's been taken up.
    still_there = await client.get("/api/v1/notes", headers=headers)
    assert len(still_there.json()["items"][0]["items"]) == 2


@pytest.mark.asyncio
async def test_convert_can_remove_the_item_it_moved(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    note = await client.post(
        "/api/v1/notes", json={"title": "Идеи для видео", "items": VIDEO_IDEAS}, headers=headers
    )
    note_id = note.json()["id"]

    await client.post(
        f"/api/v1/notes/{note_id}/convert", json={"path": [0], "remove": True}, headers=headers
    )

    remaining = (await client.get("/api/v1/notes", headers=headers)).json()["items"][0]["items"]
    assert [item["text"] for item in remaining] == ["Все форматы звука: объясняю за 9 минут"]


@pytest.mark.asyncio
async def test_convert_whole_note_uses_its_title_as_the_task(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    note = await client.post(
        "/api/v1/notes", json={"title": "Идеи для видео", "items": VIDEO_IDEAS}, headers=headers
    )

    converted = await client.post(
        f"/api/v1/notes/{note.json()['id']}/convert", json={"path": []}, headers=headers
    )

    assert converted.json()["title"] == "Идеи для видео"
    tasks = (await client.get("/api/v1/tasks?limit=1000", headers=headers)).json()["items"]
    # Root + 2 bullets + 2 nested under the second one.
    assert len(tasks) == 5


@pytest.mark.asyncio
async def test_convert_rejects_a_path_that_points_nowhere(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    note = await client.post(
        "/api/v1/notes", json={"title": "Идеи", "items": VIDEO_IDEAS}, headers=headers
    )

    response = await client.post(
        f"/api/v1/notes/{note.json()['id']}/convert", json={"path": [7]}, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_NOTE_ITEM_PATH"


@pytest.mark.asyncio
async def test_note_from_other_tenant_returns_404(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    note = await client.post(
        "/api/v1/notes", json={"title": "A's note"}, headers=_auth_headers(owner_a)
    )

    response = await client.patch(
        f"/api/v1/notes/{note.json()['id']}",
        json={"title": "Hijacked"},
        headers=_auth_headers(owner_b),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOTE_NOT_FOUND"


@pytest.mark.asyncio
async def test_note_rejects_nesting_past_the_task_depth_cap(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)

    response = await client.post(
        "/api/v1/notes",
        json={
            "title": "Слишком глубоко",
            "items": [
                {
                    "text": "1",
                    "children": [
                        {"text": "2", "children": [{"text": "3", "children": [{"text": "4"}]}]}
                    ],
                }
            ],
        },
        headers=_auth_headers(owner),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reorder_notes(client: AsyncClient, register_household: RegisterHousehold) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    a = await client.post("/api/v1/notes", json={"title": "A"}, headers=headers)
    b = await client.post("/api/v1/notes", json={"title": "B"}, headers=headers)

    response = await client.patch(
        "/api/v1/notes/reorder",
        json={"ordered_ids": [b.json()["id"], a.json()["id"]]},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    listed = await client.get("/api/v1/notes", headers=headers)
    assert [note["title"] for note in listed.json()["items"]] == [
        "B",
        "A",
    ]


@pytest.mark.asyncio
async def test_note_folders_group_notes(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)

    folder = await client.post("/api/v1/note-folders", json={"name": "Видео"}, headers=headers)
    assert folder.status_code == 201, folder.text
    folder_id = folder.json()["id"]

    in_folder = await client.post(
        "/api/v1/notes",
        json={"title": "Идеи для видео", "folder_id": folder_id},
        headers=headers,
    )
    assert in_folder.json()["folder_id"] == folder_id
    loose = await client.post("/api/v1/notes", json={"title": "Разное"}, headers=headers)
    assert loose.json()["folder_id"] is None

    folders = await client.get("/api/v1/note-folders", headers=headers)
    assert [item["name"] for item in folders.json()["items"]] == ["Видео"]


@pytest.mark.asyncio
async def test_note_folder_rename_delete_keeps_its_notes(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner = await register_household(client)
    headers = _auth_headers(owner)
    folder = await client.post("/api/v1/note-folders", json={"name": "Видео"}, headers=headers)
    folder_id = folder.json()["id"]
    await client.post(
        "/api/v1/notes", json={"title": "Идеи", "folder_id": folder_id}, headers=headers
    )

    renamed = await client.patch(
        f"/api/v1/note-folders/{folder_id}", json={"name": "Ролики"}, headers=headers
    )
    assert renamed.json()["name"] == "Ролики"

    deleted = await client.delete(f"/api/v1/note-folders/{folder_id}", headers=headers)
    assert deleted.status_code == 204

    notes = (await client.get("/api/v1/notes", headers=headers)).json()["items"]
    assert [note["title"] for note in notes] == ["Идеи"]
    assert notes[0]["folder_id"] is None


@pytest.mark.asyncio
async def test_note_folder_must_belong_to_the_same_household(
    client: AsyncClient, register_household: RegisterHousehold
) -> None:
    owner_a = await register_household(client, email="owner-a@example.com")
    owner_b = await register_household(client, email="owner-b@example.com")
    folder = await client.post(
        "/api/v1/note-folders", json={"name": "Видео"}, headers=_auth_headers(owner_b)
    )

    response = await client.post(
        "/api/v1/notes",
        json={"title": "Чужая папка", "folder_id": folder.json()["id"]},
        headers=_auth_headers(owner_a),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_NOTE_FOLDER"

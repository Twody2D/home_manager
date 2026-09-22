import uuid
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.core.errors import AppError
from home_manager.notes.models import Note, NoteFolder
from home_manager.notes.schemas import (
    NoteConvertRequest,
    NoteCreate,
    NoteFolderCreate,
    NoteFolderReorderRequest,
    NoteFolderUpdate,
    NoteReorderRequest,
    NoteUpdate,
)
from home_manager.tasks.models import Task, TaskStatus
from home_manager.tasks.service import ensure_list_in_tenant, next_order_index


class NoteNotFoundError(AppError):
    code = "NOTE_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Note not found"


class InvalidNoteItemPathError(AppError):
    code = "INVALID_NOTE_ITEM_PATH"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "path does not point at an item in this note"


class NoteFolderNotFoundError(AppError):
    code = "NOTE_FOLDER_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Note folder not found"


class InvalidNoteFolderError(AppError):
    code = "INVALID_NOTE_FOLDER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "folder_id must reference a folder in the same household"


class InvalidNoteReorderError(AppError):
    code = "INVALID_NOTE_REORDER"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "ordered_ids must exactly match the household's current notes"


async def _ensure_folder_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, folder_id: uuid.UUID | None
) -> None:
    if folder_id is None:
        return
    folder = await session.get(NoteFolder, folder_id)
    if folder is None or folder.tenant_id != tenant_id:
        raise InvalidNoteFolderError()


async def create_note(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, payload: NoteCreate
) -> Note:
    await _ensure_folder_in_tenant(session, tenant_id=tenant_id, folder_id=payload.folder_id)
    order_index = (
        await session.scalar(
            select(func.coalesce(func.max(Note.order_index), -1) + 1).where(
                Note.tenant_id == tenant_id
            )
        )
        or 0
    )
    note = Note(
        tenant_id=tenant_id,
        created_by=created_by,
        folder_id=payload.folder_id,
        title=payload.title,
        items=[item.model_dump(mode="json") for item in payload.items],
        order_index=order_index,
    )
    session.add(note)
    await session.flush()
    return note


async def list_notes(session: AsyncSession, *, tenant_id: uuid.UUID) -> list[Note]:
    query = (
        select(Note)
        .where(Note.tenant_id == tenant_id)
        .order_by(Note.order_index.asc(), Note.created_at.asc())
    )
    return list((await session.scalars(query)).all())


async def get_note(session: AsyncSession, *, tenant_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    note = await session.get(Note, note_id)
    if note is None or note.tenant_id != tenant_id:
        raise NoteNotFoundError()
    return note


async def update_note(
    session: AsyncSession, *, tenant_id: uuid.UUID, note_id: uuid.UUID, payload: NoteUpdate
) -> Note:
    note = await get_note(session, tenant_id=tenant_id, note_id=note_id)
    await _ensure_folder_in_tenant(session, tenant_id=tenant_id, folder_id=payload.folder_id)
    note.folder_id = payload.folder_id
    note.title = payload.title
    note.items = [item.model_dump(mode="json") for item in payload.items]
    await session.flush()
    return note


async def delete_note(session: AsyncSession, *, tenant_id: uuid.UUID, note_id: uuid.UUID) -> None:
    note = await get_note(session, tenant_id=tenant_id, note_id=note_id)
    await session.delete(note)
    await session.flush()


async def reorder_notes(
    session: AsyncSession, *, tenant_id: uuid.UUID, payload: NoteReorderRequest
) -> list[Note]:
    """Same exact-match-set pattern as the task reorders: fetching every note
    scoped to this tenant and requiring the payload to cover exactly that set
    doubles as the authorization check."""
    query = select(Note).where(Note.tenant_id == tenant_id)
    notes = {note.id: note for note in (await session.scalars(query)).all()}
    if set(payload.ordered_ids) != set(notes.keys()):
        raise InvalidNoteReorderError()

    for index, note_id in enumerate(payload.ordered_ids):
        notes[note_id].order_index = index
    await session.flush()
    return [notes[note_id] for note_id in payload.ordered_ids]


def _resolve_item(items: list[dict[str, Any]], path: list[int]) -> dict[str, Any]:
    current: dict[str, Any] | None = None
    level = items
    for index in path:
        if index < 0 or index >= len(level):
            raise InvalidNoteItemPathError()
        current = level[index]
        level = current.get("children") or []
    if current is None:
        raise InvalidNoteItemPathError()
    return current


def _remove_item(items: list[dict[str, Any]], path: list[int]) -> list[dict[str, Any]]:
    index, *rest = path
    if index < 0 or index >= len(items):
        raise InvalidNoteItemPathError()
    if not rest:
        return [item for i, item in enumerate(items) if i != index]
    return [
        {**item, "children": _remove_item(item.get("children") or [], rest)} if i == index else item
        for i, item in enumerate(items)
    ]


async def convert_note_item(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteConvertRequest,
) -> Task:
    """Creates a task (plus a subtask per nested bullet) from one bullet, or
    from the whole note when path is empty, and returns the root task."""
    note = await get_note(session, tenant_id=tenant_id, note_id=note_id)
    await ensure_list_in_tenant(session, tenant_id=tenant_id, list_id=payload.list_id)

    if payload.path:
        item = _resolve_item(note.items, payload.path)
        title = item["text"]
        children = item.get("children") or []
    else:
        title = note.title
        children = note.items

    order_index = await next_order_index(
        session, tenant_id=tenant_id, list_id=payload.list_id, parent_task_id=None
    )
    root = Task(
        tenant_id=tenant_id,
        created_by=created_by,
        # Same default as adding a task by hand: it's yours unless changed.
        assigned_to=created_by,
        budget_owner_user_id=created_by,
        title=title[:200],
        status=TaskStatus.PENDING,
        list_id=payload.list_id,
        order_index=order_index,
    )
    session.add(root)
    await session.flush()

    async def add_children(items: list[dict[str, Any]], parent: Task) -> None:
        for index, child_item in enumerate(items):
            child = Task(
                tenant_id=tenant_id,
                created_by=created_by,
                assigned_to=created_by,
                budget_owner_user_id=created_by,
                title=child_item["text"][:200],
                status=TaskStatus.PENDING,
                list_id=payload.list_id,
                parent_task_id=parent.id,
                order_index=index,
            )
            session.add(child)
            await session.flush()
            await add_children(child_item.get("children") or [], child)

    await add_children(children, root)

    if payload.remove:
        # Converting the whole note leaves an empty note rather than deleting
        # it — the title is often the category ("Идеи для видео"), which is
        # still wanted once its current contents have moved on.
        note.items = _remove_item(note.items, payload.path) if payload.path else []
        await session.flush()

    return root


async def create_note_folder(
    session: AsyncSession, *, tenant_id: uuid.UUID, created_by: uuid.UUID, payload: NoteFolderCreate
) -> NoteFolder:
    order_index = (
        await session.scalar(
            select(func.coalesce(func.max(NoteFolder.order_index), -1) + 1).where(
                NoteFolder.tenant_id == tenant_id
            )
        )
        or 0
    )
    folder = NoteFolder(
        tenant_id=tenant_id, created_by=created_by, name=payload.name, order_index=order_index
    )
    session.add(folder)
    await session.flush()
    return folder


async def list_note_folders(session: AsyncSession, *, tenant_id: uuid.UUID) -> list[NoteFolder]:
    query = (
        select(NoteFolder)
        .where(NoteFolder.tenant_id == tenant_id)
        .order_by(NoteFolder.order_index.asc(), NoteFolder.created_at.asc())
    )
    return list((await session.scalars(query)).all())


async def get_note_folder(
    session: AsyncSession, *, tenant_id: uuid.UUID, folder_id: uuid.UUID
) -> NoteFolder:
    folder = await session.get(NoteFolder, folder_id)
    if folder is None or folder.tenant_id != tenant_id:
        raise NoteFolderNotFoundError()
    return folder


async def update_note_folder(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    folder_id: uuid.UUID,
    payload: NoteFolderUpdate,
) -> NoteFolder:
    folder = await get_note_folder(session, tenant_id=tenant_id, folder_id=folder_id)
    folder.name = payload.name
    await session.flush()
    return folder


async def delete_note_folder(
    session: AsyncSession, *, tenant_id: uuid.UUID, folder_id: uuid.UUID
) -> None:
    folder = await get_note_folder(session, tenant_id=tenant_id, folder_id=folder_id)
    # Notes in it are NOT deleted — Note.folder_id's ondelete="SET NULL"
    # moves them out of any folder, same as task lists do.
    await session.delete(folder)
    await session.flush()


async def reorder_note_folders(
    session: AsyncSession, *, tenant_id: uuid.UUID, payload: NoteFolderReorderRequest
) -> list[NoteFolder]:
    query = select(NoteFolder).where(NoteFolder.tenant_id == tenant_id)
    folders = {folder.id: folder for folder in (await session.scalars(query)).all()}
    if set(payload.ordered_ids) != set(folders.keys()):
        raise InvalidNoteReorderError()

    for index, folder_id in enumerate(payload.ordered_ids):
        folders[folder_id].order_index = index
    await session.flush()
    return [folders[folder_id] for folder_id in payload.ordered_ids]

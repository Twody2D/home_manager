import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.db.session import get_db_session
from home_manager.notes import service
from home_manager.notes.schemas import (
    NoteConvertRequest,
    NoteCreate,
    NoteReorderRequest,
    NoteResponse,
    NotesResponse,
    NoteUpdate,
)
from home_manager.tasks.schemas import TaskResponse

router = APIRouter(prefix="/notes", tags=["notes"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate, current_user: CurrentUser, session: DbSession
) -> NoteResponse:
    note = await service.create_note(
        session, tenant_id=current_user.tenant_id, created_by=current_user.id, payload=payload
    )
    await session.commit()
    return NoteResponse.model_validate(note)


@router.get("", response_model=NotesResponse)
async def list_notes(current_user: CurrentUser, session: DbSession) -> NotesResponse:
    items = await service.list_notes(session, tenant_id=current_user.tenant_id)
    return NotesResponse(items=[NoteResponse.model_validate(item) for item in items])


@router.patch("/reorder", response_model=list[NoteResponse])
async def reorder_notes(
    payload: NoteReorderRequest, current_user: CurrentUser, session: DbSession
) -> list[NoteResponse]:
    # Registered before "/{note_id}" so "reorder" is never parsed as an id.
    notes = await service.reorder_notes(session, tenant_id=current_user.tenant_id, payload=payload)
    await session.commit()
    return [NoteResponse.model_validate(note) for note in notes]


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID, payload: NoteUpdate, current_user: CurrentUser, session: DbSession
) -> NoteResponse:
    note = await service.update_note(
        session, tenant_id=current_user.tenant_id, note_id=note_id, payload=payload
    )
    await session.commit()
    return NoteResponse.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: uuid.UUID, current_user: CurrentUser, session: DbSession) -> None:
    await service.delete_note(session, tenant_id=current_user.tenant_id, note_id=note_id)
    await session.commit()


@router.post("/{note_id}/convert", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def convert_note_item(
    note_id: uuid.UUID,
    payload: NoteConvertRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> TaskResponse:
    task = await service.convert_note_item(
        session,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        note_id=note_id,
        payload=payload,
    )
    await session.commit()
    return TaskResponse.model_validate(task)

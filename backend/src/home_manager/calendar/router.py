import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.calendar import service
from home_manager.calendar.schemas import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
)
from home_manager.db.session import get_db_session

router = APIRouter(prefix="/calendar/events", tags=["calendar"])

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CalendarEventCreate, current_user: CurrentUser, session: DbSession
) -> CalendarEventResponse:
    event = await service.create_event(
        session, tenant_id=current_user.tenant_id, user_id=current_user.id, payload=payload
    )
    await session.commit()
    return CalendarEventResponse.model_validate(event)


@router.get("", response_model=list[CalendarEventResponse])
async def list_events(
    current_user: CurrentUser,
    session: DbSession,
    user_id: uuid.UUID | None = None,
    starts_before: Annotated[datetime | None, Query()] = None,
    ends_after: Annotated[datetime | None, Query()] = None,
) -> list[CalendarEventResponse]:
    events = await service.list_events(
        session,
        tenant_id=current_user.tenant_id,
        user_id=user_id,
        starts_before=starts_before,
        ends_after=ends_after,
    )
    return [CalendarEventResponse.model_validate(event) for event in events]


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: uuid.UUID, current_user: CurrentUser, session: DbSession
) -> CalendarEventResponse:
    event = await service.get_event(session, tenant_id=current_user.tenant_id, event_id=event_id)
    return CalendarEventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: uuid.UUID, payload: CalendarEventUpdate, current_user: CurrentUser, session: DbSession
) -> CalendarEventResponse:
    event = await service.update_event(
        session,
        tenant_id=current_user.tenant_id,
        requesting_user_id=current_user.id,
        event_id=event_id,
        payload=payload,
    )
    await session.commit()
    return CalendarEventResponse.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: uuid.UUID, current_user: CurrentUser, session: DbSession) -> None:
    await service.delete_event(
        session,
        tenant_id=current_user.tenant_id,
        requesting_user_id=current_user.id,
        event_id=event_id,
    )
    await session.commit()

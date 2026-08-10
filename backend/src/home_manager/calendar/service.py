import uuid
from datetime import datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from home_manager.calendar.models import CalendarEvent
from home_manager.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from home_manager.core.errors import AppError


class CalendarEventNotFoundError(AppError):
    code = "CALENDAR_EVENT_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Calendar event not found"


class InvalidCalendarWindowError(AppError):
    code = "INVALID_CALENDAR_WINDOW"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "end_at must not be before start_at"


class NotEventOwnerError(AppError):
    code = "NOT_EVENT_OWNER"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You can only modify your own calendar events"


async def create_event(
    session: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID, payload: CalendarEventCreate
) -> CalendarEvent:
    event = CalendarEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        start_at=payload.start_at,
        end_at=payload.end_at,
        all_day=payload.all_day,
        location=payload.location,
        recurrence=payload.recurrence,
    )
    session.add(event)
    await session.flush()
    return event


async def get_event(
    session: AsyncSession, *, tenant_id: uuid.UUID, event_id: uuid.UUID
) -> CalendarEvent:
    event = await session.get(CalendarEvent, event_id)
    if event is None or event.tenant_id != tenant_id:
        raise CalendarEventNotFoundError()
    return event


async def list_events(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    starts_before: datetime | None,
    ends_after: datetime | None,
) -> list[CalendarEvent]:
    query = select(CalendarEvent).where(CalendarEvent.tenant_id == tenant_id)

    if user_id is not None:
        query = query.where(CalendarEvent.user_id == user_id)
    # Overlap with the [ends_after, starts_before] window, when given.
    if starts_before is not None:
        query = query.where(CalendarEvent.start_at < starts_before)
    if ends_after is not None:
        query = query.where(CalendarEvent.end_at > ends_after)

    query = query.order_by(CalendarEvent.start_at)
    return list((await session.scalars(query)).all())


async def update_event(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: CalendarEventUpdate,
) -> CalendarEvent:
    event = await get_event(session, tenant_id=tenant_id, event_id=event_id)
    if event.user_id != requesting_user_id:
        raise NotEventOwnerError()

    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    new_start = updates.get("start_at", event.start_at)
    new_end = updates.get("end_at", event.end_at)
    if new_end < new_start:
        raise InvalidCalendarWindowError()

    for field, value in updates.items():
        setattr(event, field, value)

    await session.flush()
    return event


async def delete_event(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    event_id: uuid.UUID,
) -> None:
    event = await get_event(session, tenant_id=tenant_id, event_id=event_id)
    if event.user_id != requesting_user_id:
        raise NotEventOwnerError()
    await session.delete(event)
    await session.flush()

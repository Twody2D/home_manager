import uuid
from typing import Literal

from pydantic import BaseModel, Field

from home_manager.calendar.models import CalendarEventType
from home_manager.calendar.schemas import CalendarEventCreate


class CreateTaskIntent(BaseModel):
    intent: Literal["create_task"] = "create_task"
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0)


class ScheduleEventItem(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    event_type: CalendarEventType
    title: str | None = Field(default=None, max_length=200)


class CreateScheduleIntent(BaseModel):
    intent: Literal["create_schedule"] = "create_schedule"
    # Bounded the same as the calendar bulk-create endpoint it feeds into.
    events: list[ScheduleEventItem] = Field(min_length=1, max_length=60)


class UnknownIntent(BaseModel):
    intent: Literal["unknown"] = "unknown"
    raw_message: str


AssistantIntent = CreateTaskIntent | CreateScheduleIntent | UnknownIntent


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # ISO 8601 with UTC offset, e.g. "2026-08-10T22:30:00+03:00" — lets the
    # assistant resolve "tomorrow"/"Monday" and store shift times in the
    # user's actual local time instead of guessing a timezone server-side.
    client_now: str | None = Field(default=None, max_length=40)
    # The UI's current language ("en"/"ru") — only used to pick which fixed
    # reply strings execute_intent responds with, unrelated to what language
    # the user's own message happens to be in.
    locale: str = Field(default="en", max_length=10)


class AssistantReply(BaseModel):
    reply: str
    task_id: uuid.UUID | None = None
    # Parsed but not yet saved — the frontend shows these for the user to
    # review/trim, then submits them itself via the normal calendar bulk
    # endpoint. Nothing from a create_schedule intent is persisted directly
    # by the assistant; a small free LLM is not reliable enough for that.
    proposed_events: list[CalendarEventCreate] | None = None

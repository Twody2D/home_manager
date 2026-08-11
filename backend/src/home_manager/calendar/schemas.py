import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from home_manager.calendar.models import CalendarEventType


class CalendarEventCreate(BaseModel):
    event_type: CalendarEventType
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)
    # Defaults to the creator. Set to another household member's id to put
    # the same event on their calendar instead — e.g. one partner adding a
    # shared plan to both calendars submits it twice, once per user_id.
    # Validated to be a member of the same household in the service layer,
    # the same way tasks.assigned_to already is.
    user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _validate_window(self) -> Self:
        if self.end_at < self.start_at:
            raise ValueError("end_at must not be before start_at")
        return self


class CalendarEventBulkCreate(BaseModel):
    # Bounded so a single request can't be used to hammer the DB with an
    # unbounded insert — covers the real use case (a few weeks of shifts)
    # with headroom to spare.
    events: list[CalendarEventCreate] = Field(min_length=1, max_length=60)


class CalendarEventUpdate(BaseModel):
    event_type: CalendarEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    event_type: CalendarEventType
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    all_day: bool
    location: str | None
    recurrence: str | None
    created_at: datetime
    updated_at: datetime

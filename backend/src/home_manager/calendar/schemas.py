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

    @model_validator(mode="after")
    def _validate_window(self) -> Self:
        if self.end_at < self.start_at:
            raise ValueError("end_at must not be before start_at")
        return self


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

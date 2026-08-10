import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from home_manager.tasks.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    duration_minutes: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    preferred_start: datetime | None = None
    preferred_end: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate_preferred_window(self) -> Self:
        if (
            self.preferred_start is not None
            and self.preferred_end is not None
            and self.preferred_end < self.preferred_start
        ):
            raise ValueError("preferred_end must not be before preferred_start")
        return self


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    preferred_start: datetime | None = None
    preferred_end: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    recurrence: str | None = Field(default=None, max_length=200)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: uuid.UUID | None
    assigned_to: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    duration_minutes: int | None
    due_at: datetime | None
    preferred_start: datetime | None
    preferred_end: datetime | None
    location: str | None
    recurrence: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int

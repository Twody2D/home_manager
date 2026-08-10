import uuid
from datetime import date as date_
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from home_manager.tasks.models import TaskPriority


class ScheduledTaskEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: uuid.UUID
    title: str
    priority: TaskPriority
    start_at: datetime
    end_at: datetime
    score: float


class UnscheduledTaskEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: uuid.UUID
    title: str
    priority: TaskPriority
    reason: str


class DailyPlanResponse(BaseModel):
    date: date_
    scheduled: list[ScheduledTaskEntry]
    unscheduled: list[UnscheduledTaskEntry]

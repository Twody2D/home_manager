import uuid
from typing import Literal

from pydantic import BaseModel, Field


class CreateTaskIntent(BaseModel):
    intent: Literal["create_task"] = "create_task"
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0)


class UnknownIntent(BaseModel):
    intent: Literal["unknown"] = "unknown"
    raw_message: str


AssistantIntent = CreateTaskIntent | UnknownIntent


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AssistantReply(BaseModel):
    reply: str
    task_id: uuid.UUID | None = None

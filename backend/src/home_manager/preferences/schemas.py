import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from home_manager.preferences.models import EnergyPattern


class PreferencesUpdate(BaseModel):
    working_hours_start: time | None = None
    working_hours_end: time | None = None
    sleep_start: time | None = None
    sleep_end: time | None = None
    preferred_categories: list[str] | None = None
    disliked_categories: list[str] | None = None
    energy_pattern: EnergyPattern | None = None
    task_speed_multiplier: float | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=5000)


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    working_hours_start: time | None
    working_hours_end: time | None
    sleep_start: time | None
    sleep_end: time | None
    preferred_categories: list[str]
    disliked_categories: list[str]
    energy_pattern: EnergyPattern
    task_speed_multiplier: float
    notes: str | None

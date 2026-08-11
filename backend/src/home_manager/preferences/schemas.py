import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from home_manager.preferences.models import EnergyPattern


class PreferencesUpdate(BaseModel):
    workplace: str | None = Field(default=None, max_length=200)
    working_hours_start: time | None = None
    working_hours_end: time | None = None
    sleep_start: time | None = None
    sleep_end: time | None = None
    energy_pattern: EnergyPattern | None = None
    task_speed_multiplier: float | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=5000)


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    workplace: str | None
    working_hours_start: time | None
    working_hours_end: time | None
    sleep_start: time | None
    sleep_end: time | None
    energy_pattern: EnergyPattern
    task_speed_multiplier: float
    notes: str | None

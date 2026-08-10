from typing import Literal

from pydantic import BaseModel

SmartHomeCommand = Literal["turn_on", "turn_off", "toggle"]


class SmartHomeDevice(BaseModel):
    entity_id: str
    name: str
    domain: str
    state: str
    is_on: bool

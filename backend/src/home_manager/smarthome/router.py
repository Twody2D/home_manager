from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from home_manager.auth.dependencies import get_current_user
from home_manager.auth.models import User
from home_manager.smarthome import service
from home_manager.smarthome.schemas import SmartHomeCommand, SmartHomeDevice

# Any authenticated household member can view/control devices — the same
# shared-trust model already used for tasks and calendar. Unlike those,
# devices aren't stored per-tenant in our DB at all: there's one configured
# smart home hub per deployment (see smarthome/factory.py). That's fine for
# a single household; a genuinely multi-tenant SaaS would need per-tenant
# hub credentials, which is out of scope until that's an actual requirement.
router = APIRouter(prefix="/smarthome", tags=["smarthome"])

CurrentUser = Annotated[User, Depends(get_current_user)]


class SmartHomeCommandRequest(BaseModel):
    command: SmartHomeCommand


@router.get("/devices", response_model=list[SmartHomeDevice])
async def list_devices(current_user: CurrentUser) -> list[SmartHomeDevice]:
    return await service.list_devices()


@router.post("/devices/{entity_id}/command", response_model=SmartHomeDevice)
async def execute_command(
    entity_id: str, payload: SmartHomeCommandRequest, current_user: CurrentUser
) -> SmartHomeDevice:
    return await service.execute_command(entity_id=entity_id, command=payload.command)

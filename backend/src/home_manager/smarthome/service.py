from home_manager.smarthome.errors import SmartHomeDeviceNotFoundError
from home_manager.smarthome.factory import get_smart_home_provider
from home_manager.smarthome.schemas import SmartHomeCommand, SmartHomeDevice

# Deliberately narrow: this is a generic on/off/toggle endpoint, so only
# domains where that's a safe, reversible action are ever exposed — locks,
# alarms, climate, media players, etc. stay out of scope for now.
CONTROLLABLE_DOMAINS = {"light", "switch"}


def _domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


async def list_devices() -> list[SmartHomeDevice]:
    provider = get_smart_home_provider()
    devices = await provider.list_devices()
    return [device for device in devices if device.domain in CONTROLLABLE_DOMAINS]


async def execute_command(*, entity_id: str, command: SmartHomeCommand) -> SmartHomeDevice:
    if _domain_of(entity_id) not in CONTROLLABLE_DOMAINS:
        raise SmartHomeDeviceNotFoundError()

    provider = get_smart_home_provider()
    return await provider.execute_command(entity_id=entity_id, command=command)

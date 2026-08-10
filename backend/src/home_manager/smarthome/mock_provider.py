from home_manager.smarthome.errors import SmartHomeDeviceNotFoundError
from home_manager.smarthome.schemas import SmartHomeCommand, SmartHomeDevice

_INITIAL_DEVICES: list[SmartHomeDevice] = [
    SmartHomeDevice(
        entity_id="light.living_room",
        name="Living Room Light",
        domain="light",
        state="off",
        is_on=False,
    ),
    SmartHomeDevice(
        entity_id="switch.kettle", name="Kettle", domain="switch", state="off", is_on=False
    ),
]


class MockSmartHomeProvider:
    """In-memory, network-free stand-in for a real smart home hub.

    Holds a couple of fake devices with mutable state for the life of the
    process, so the devices UI (and dev/CI) never depend on a real Home
    Assistant instance being reachable.
    """

    def __init__(self) -> None:
        self._devices = {device.entity_id: device for device in _INITIAL_DEVICES}

    async def list_devices(self) -> list[SmartHomeDevice]:
        return list(self._devices.values())

    async def execute_command(
        self, *, entity_id: str, command: SmartHomeCommand
    ) -> SmartHomeDevice:
        device = self._devices.get(entity_id)
        if device is None:
            raise SmartHomeDeviceNotFoundError()

        is_on = {"turn_on": True, "turn_off": False, "toggle": not device.is_on}[command]
        updated = device.model_copy(update={"is_on": is_on, "state": "on" if is_on else "off"})
        self._devices[entity_id] = updated
        return updated

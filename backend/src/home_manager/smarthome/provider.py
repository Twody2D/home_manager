from typing import Protocol

from home_manager.smarthome.schemas import SmartHomeCommand, SmartHomeDevice


class SmartHomeProvider(Protocol):
    """Abstraction over a smart home hub (Home Assistant, Yandex Smart
    Home, ...).

    Implementations are pure request/response adapters over that hub's own
    API — no business rules here (which domains are safe to expose, who's
    allowed to control what) belong in home_manager.smarthome.service, not
    in a provider.
    """

    async def list_devices(self) -> list[SmartHomeDevice]: ...

    async def execute_command(
        self, *, entity_id: str, command: SmartHomeCommand
    ) -> SmartHomeDevice: ...

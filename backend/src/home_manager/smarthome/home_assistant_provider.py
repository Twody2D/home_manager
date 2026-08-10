from typing import Any

import httpx

from home_manager.smarthome.errors import SmartHomeProviderError
from home_manager.smarthome.schemas import SmartHomeCommand, SmartHomeDevice

# Only entity domains the service layer allows through reach this class at
# all (see smarthome/service.py) — this is just a second, independent check
# so a provider on its own is never the only thing standing between a
# request and controlling something unsafe (locks, alarms, ...).
CONTROLLABLE_DOMAINS = {"light", "switch"}


def _domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def _to_device(state: dict[str, Any]) -> SmartHomeDevice:
    entity_id = state["entity_id"]
    attributes = state.get("attributes") or {}
    return SmartHomeDevice(
        entity_id=entity_id,
        name=attributes.get("friendly_name", entity_id),
        domain=_domain_of(entity_id),
        state=state.get("state", "unknown"),
        is_on=state.get("state") == "on",
    )


class HomeAssistantProvider:
    """Talks to a real Home Assistant instance over its REST API."""

    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def list_devices(self) -> list[SmartHomeDevice]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self._base_url}/api/states", headers=self._headers)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise SmartHomeProviderError() from exc

        states: list[dict[str, Any]] = response.json()
        return [
            _to_device(state)
            for state in states
            if _domain_of(state.get("entity_id", "")) in CONTROLLABLE_DOMAINS
        ]

    async def execute_command(
        self, *, entity_id: str, command: SmartHomeCommand
    ) -> SmartHomeDevice:
        domain = _domain_of(entity_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                command_response = await client.post(
                    f"{self._base_url}/api/services/{domain}/{command}",
                    headers=self._headers,
                    json={"entity_id": entity_id},
                )
                command_response.raise_for_status()

                state_response = await client.get(
                    f"{self._base_url}/api/states/{entity_id}", headers=self._headers
                )
                state_response.raise_for_status()
            except httpx.HTTPError as exc:
                raise SmartHomeProviderError() from exc

        return _to_device(state_response.json())

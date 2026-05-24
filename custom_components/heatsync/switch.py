"""Switch platform — quiet mode, away."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatSyncCoordinator = entry.runtime_data
    indoor = next((a for a, d in coordinator.data.items() if d.get("type") == "indoor"), None)
    if indoor:
        async_add_entities([
            QuietModeSwitch(coordinator, indoor),
            AwaySwitch(coordinator, indoor),
        ])


class QuietModeSwitch(HeatSyncEntity, SwitchEntity):
    _attr_name = "Quiet mode"
    _attr_icon = "mdi:volume-off"

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_quiet_mode"

    @property
    def is_on(self) -> bool | None:
        v = self.device.get("quietMode")
        return bool(v) if v is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        # TODO: device's POST endpoint for quiet_mode lives on MQTT only
        # at the moment — added as an HTTP endpoint in a follow-up.
        # For now: write via the device's MQTT topic if a broker is
        # present. As a placeholder, this raises NotImplementedError so
        # the UI shows the failure clearly rather than silently failing.
        raise NotImplementedError(
            "Quiet mode write needs the firmware's /api/control/quiet-mode "
            "HTTP endpoint (firmware MQTT-only currently).",
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Quiet mode write needs the firmware's /api/control/quiet-mode "
            "HTTP endpoint (firmware MQTT-only currently).",
        )


class AwaySwitch(HeatSyncEntity, SwitchEntity):
    _attr_name = "Away"
    _attr_icon = "mdi:home-export-outline"

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_away"

    @property
    def is_on(self) -> bool | None:
        # The "away" state isn't broadcast from the bus — it's tracked
        # in the device's app config and surfaced via /api/cost/status
        # or similar. We optimistically read it from /api/live if present.
        v = self.device.get("awayActive")
        return bool(v) if v is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_away(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_away(False)
        await self.coordinator.async_request_refresh()

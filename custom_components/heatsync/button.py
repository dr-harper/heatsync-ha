"""Button platform — one-shot actions (heating boost, DHW boost)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
            HeatingBoostButton(coordinator, indoor),
            DhwBoostButton(coordinator, indoor),
        ])


class HeatingBoostButton(HeatSyncEntity, ButtonEntity):
    _attr_name = "Heating boost"
    _attr_icon = "mdi:fire-circle"

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_heating_boost"

    async def async_press(self) -> None:
        await self.coordinator.client.heating_boost()
        await self.coordinator.async_request_refresh()


class DhwBoostButton(HeatSyncEntity, ButtonEntity):
    _attr_name = "Hot water boost"
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_dhw_boost"

    async def async_press(self) -> None:
        await self.coordinator.client.dhw_boost()
        await self.coordinator.async_request_refresh()

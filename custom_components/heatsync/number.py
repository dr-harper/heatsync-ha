"""Number platform — water-law offset, flow target."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
            WaterLawOffsetNumber(coordinator, indoor),
        ])


class WaterLawOffsetNumber(HeatSyncEntity, NumberEntity):
    _attr_name = "Water-law offset"
    _attr_icon = "mdi:tune-vertical"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = -5
    _attr_native_max_value = 5
    _attr_native_step = 0.5
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = (
            f"{coordinator.entry.unique_id}_{address}_water_law_offset"
        )

    @property
    def native_value(self) -> float | None:
        return self.device.get("waterLawOffset")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_water_law_offset(value)
        await self.coordinator.async_request_refresh()

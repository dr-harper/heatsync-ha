"""Climate platform — the heat pump's main mode/target control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity

# Map between the device's lowercase mode strings (from /api/live) and
# HA's HVACMode enum. The device speaks: off | heat | cool | auto.
_MODE_TO_HA = {
    "off":  HVACMode.OFF,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "auto": HVACMode.AUTO,
}
_HA_TO_MODE = {v: k for k, v in _MODE_TO_HA.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatSyncCoordinator = entry.runtime_data
    # One climate entity per indoor unit. Most installs have one.
    indoor_addrs = [
        addr for addr, dev in coordinator.data.items()
        if dev.get("type") == "indoor"
    ]
    async_add_entities([HeatSyncClimate(coordinator, a) for a in indoor_addrs])


class HeatSyncClimate(HeatSyncEntity, ClimateEntity):
    _attr_name = "Heat pump"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
    _attr_min_temp = 16
    _attr_max_temp = 32
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_climate"

    @property
    def hvac_mode(self) -> HVACMode | None:
        if not self.device.get("power"):
            return HVACMode.OFF
        return _MODE_TO_HA.get(self.device.get("mode") or "", HVACMode.OFF)

    @property
    def current_temperature(self) -> float | None:
        return self.device.get("roomTemp")

    @property
    def target_temperature(self) -> float | None:
        return self.device.get("targetTemp")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        mode = _HA_TO_MODE.get(hvac_mode, "off")
        await self.coordinator.client.set_heating_mode(mode)
        # Optimistic update — show the new mode immediately rather than
        # waiting for the next 5-s poll cycle to confirm.
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.client.set_heating_target(float(temp))
        await self.coordinator.async_request_refresh()

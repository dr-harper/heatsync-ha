"""Water-heater platform — DHW power, target, mode."""
from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_HEAT_PUMP,
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity

# The device's modes (eco/standard/power/force) map onto HA's allowed
# water_heater states. Standard ↔ heat_pump, Power ↔ performance,
# Force ↔ performance (booster).
_MODE_TO_HA = {
    "eco":      STATE_ECO,
    "standard": STATE_HEAT_PUMP,
    "power":    STATE_PERFORMANCE,
    "force":    STATE_PERFORMANCE,
}
_HA_TO_MODE = {
    STATE_ECO:         "eco",
    STATE_HEAT_PUMP:   "standard",
    STATE_PERFORMANCE: "power",
    STATE_OFF:         None,  # off = power off, not a mode
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatSyncCoordinator = entry.runtime_data
    indoor_addrs = [
        addr for addr, dev in coordinator.data.items()
        if dev.get("type") == "indoor"
    ]
    async_add_entities([HeatSyncWaterHeater(coordinator, a) for a in indoor_addrs])


class HeatSyncWaterHeater(HeatSyncEntity, WaterHeaterEntity):
    _attr_name = "Hot water"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )
    _attr_operation_list = [STATE_OFF, STATE_ECO, STATE_HEAT_PUMP, STATE_PERFORMANCE]
    _attr_min_temp = 30
    _attr_max_temp = 65

    def __init__(self, coordinator: HeatSyncCoordinator, address: str) -> None:
        super().__init__(coordinator, address)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{address}_dhw"

    @property
    def current_temperature(self) -> float | None:
        return self.device.get("tankTemp")

    @property
    def target_temperature(self) -> float | None:
        return self.device.get("dhwTarget")

    @property
    def current_operation(self) -> str | None:
        if not self.device.get("dhwPower"):
            return STATE_OFF
        return _MODE_TO_HA.get(self.device.get("dhwMode") or "")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.client.set_dhw_target(float(temp))
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_OFF:
            await self.coordinator.client.set_dhw_power(False)
        else:
            mode = _HA_TO_MODE.get(operation_mode)
            if mode is not None:
                await self.coordinator.client.set_dhw_power(True)
                await self.coordinator.client.set_dhw_mode(mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.coordinator.client.set_dhw_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.set_dhw_power(False)
        await self.coordinator.async_request_refresh()

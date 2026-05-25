"""Water-heater platform — DHW power, target, mode."""
from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity

# Samsung's DHW mode names verbatim from the wired controller's UI.
# HA's water_heater platform allows arbitrary mode strings — they show
# up exactly as listed below in the dropdown. We don't map to HA's
# built-in STATE_HEAT_PUMP / STATE_PERFORMANCE constants because those
# rename "Standard" → "Heat pump" and "Power" → "Performance" in the
# UI, which doesn't match what Samsung's own docs + wired remote
# call them. Confusing for users cross-referencing.
#
# Note: not every unit supports all four modes — Samsung publishes
# only what your model actually accepts via the bus. Selecting an
# unsupported mode silently no-ops; the bus echo will show the unit
# stayed on its previous mode.
DHW_MODES = ["Eco", "Standard", "Power", "Force"]

# Bus state is lowercase (the firmware lowercases on the MQTT publish
# path). UI mode label is capitalised. This dict bridges the two.
_BUS_TO_LABEL = {m.lower(): m for m in DHW_MODES}
_LABEL_TO_BUS = {m: m.lower() for m in DHW_MODES}


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
    _attr_operation_list = [STATE_OFF, *DHW_MODES]
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
        # Bus reports lowercase ("standard"); UI uses Samsung's
        # capitalised label ("Standard"). Fall back to the raw value
        # if it's an unrecognised mode rather than dropping it.
        raw = self.device.get("dhwMode") or ""
        return _BUS_TO_LABEL.get(raw, raw or None)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.client.set_dhw_target(float(temp))
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        if operation_mode == STATE_OFF:
            await self.coordinator.client.set_dhw_power(False)
        else:
            bus_mode = _LABEL_TO_BUS.get(operation_mode)
            if bus_mode is not None:
                await self.coordinator.client.set_dhw_power(True)
                await self.coordinator.client.set_dhw_mode(bus_mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.coordinator.client.set_dhw_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.set_dhw_power(False)
        await self.coordinator.async_request_refresh()

"""Binary sensor platform — pump, defrost, fault, compressor."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity


@dataclass(frozen=True)
class HSBinaryDef:
    name: str
    field: str
    device_type: str
    description: BinarySensorEntityDescription


INDOOR: list[HSBinaryDef] = [
    HSBinaryDef("Water pump", "pumpOn", "indoor",
        BinarySensorEntityDescription(key="pumpOn",
            device_class=BinarySensorDeviceClass.RUNNING)),
]
OUTDOOR: list[HSBinaryDef] = [
    HSBinaryDef("Compressor", "compOn", "outdoor",
        BinarySensorEntityDescription(key="compOn",
            device_class=BinarySensorDeviceClass.RUNNING)),
    HSBinaryDef("Fault", "fault", "outdoor",
        BinarySensorEntityDescription(key="fault",
            device_class=BinarySensorDeviceClass.PROBLEM)),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatSyncCoordinator = entry.runtime_data
    indoor  = next((a for a, d in coordinator.data.items() if d.get("type") == "indoor"), None)
    outdoor = next((a for a, d in coordinator.data.items() if d.get("type") == "outdoor"), None)

    entities: list[HeatSyncBinarySensor] = []
    if indoor:
        for b in INDOOR:
            entities.append(HeatSyncBinarySensor(coordinator, indoor, b))
    if outdoor:
        for b in OUTDOOR:
            entities.append(HeatSyncBinarySensor(coordinator, outdoor, b))
    # Fault is the synthetic errorCode != 0 — derive it client-side since
    # /api/live exposes errorCode but not a precomputed bool.
    async_add_entities(entities)


class HeatSyncBinarySensor(HeatSyncEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: HeatSyncCoordinator,
        address: str,
        definition: HSBinaryDef,
    ) -> None:
        super().__init__(coordinator, address)
        self._def = definition
        self.entity_description = definition.description
        self._attr_name = definition.name
        self._attr_unique_id = (
            f"{coordinator.entry.unique_id}_{address}_{definition.field}"
        )

    @property
    def is_on(self) -> bool | None:
        v = self.device.get(self._def.field)
        # The "fault" entity reads errorCode under the hood — derive
        # a bool from "is it non-zero, non-null".
        if self._def.field == "fault":
            ec = self.device.get("errorCode")
            return bool(ec) and ec != 0
        return bool(v) if v is not None else None

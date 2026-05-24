"""Sensor platform — every read-only metric from the device.

Defined as a flat list of `SensorDef` rows: which field of /api/live to
read, what type of NASA address it lives under, and what HA metadata
(unit, device_class) to expose. Each row becomes a HeatSyncSensor
entity at setup time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HeatSyncCoordinator
from .entity import HeatSyncEntity


@dataclass(frozen=True)
class HSSensorDef:
    """How to map one /api/live field to a HA sensor entity."""
    name: str
    field: str            # key inside the per-device dict
    device_type: str      # "indoor" or "outdoor"
    description: SensorEntityDescription


def _t(name: str, field: str, dt: str) -> HSSensorDef:
    """Helper for °C temperature sensors (the most common case)."""
    return HSSensorDef(
        name=name, field=field, device_type=dt,
        description=SensorEntityDescription(
            key=field,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            suggested_display_precision=1,
        ),
    )


# Indoor-unit sensors (NASA address 20.xx.xx).
INDOOR_SENSORS: list[HSSensorDef] = [
    _t("Eva in",            "evaIn",        "indoor"),
    _t("Eva out",           "evaOut",       "indoor"),
    _t("Tank temp",         "tankTemp",     "indoor"),
    _t("Flow actual",       "flowActual",   "indoor"),
    _t("Water inlet",       "waterInlet",   "indoor"),
    _t("Water-law target",  "waterLawTarget","indoor"),
    HSSensorDef(
        name="Flow rate", field="flowRate", device_type="indoor",
        description=SensorEntityDescription(
            key="flowRate",
            device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
            suggested_display_precision=1,
        ),
    ),
    HSSensorDef(
        name="Humidity", field="humidity", device_type="indoor",
        description=SensorEntityDescription(
            key="humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
        ),
    ),
    HSSensorDef(
        name="Thermal power", field="thermalW", device_type="indoor",
        description=SensorEntityDescription(
            key="thermalW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
        ),
    ),
]

# Outdoor-unit sensors (10.xx.xx) — the electrical + compressor side.
OUTDOOR_SENSORS: list[HSSensorDef] = [
    _t("Outdoor temp",    "outdoorTemp",     "outdoor"),
    _t("Discharge temp",  "dischargeTemp",   "outdoor"),
    _t("Suction temp",    "suctionTemp",     "outdoor"),
    HSSensorDef(
        name="Power", field="powerW", device_type="outdoor",
        description=SensorEntityDescription(
            key="powerW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
        ),
    ),
    HSSensorDef(
        name="Energy", field="energyKwh", device_type="outdoor",
        description=SensorEntityDescription(
            key="energyKwh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        ),
    ),
    HSSensorDef(
        name="Current", field="currentA", device_type="outdoor",
        description=SensorEntityDescription(
            key="currentA",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            suggested_display_precision=2,
        ),
    ),
    HSSensorDef(
        name="Voltage", field="voltageV", device_type="outdoor",
        description=SensorEntityDescription(
            key="voltageV",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        ),
    ),
    HSSensorDef(
        name="Compressor freq", field="compFreq", device_type="outdoor",
        description=SensorEntityDescription(
            key="compFreq",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
        ),
    ),
    HSSensorDef(
        name="Fan RPM", field="fanRpm", device_type="outdoor",
        description=SensorEntityDescription(
            key="fanRpm",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        ),
    ),
    HSSensorDef(
        name="Cycles per hour", field="cyclesPerHour", device_type="outdoor",
        description=SensorEntityDescription(
            key="cyclesPerHour",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="/h",
        ),
    ),
    HSSensorDef(
        name="Error code", field="errorCode", device_type="outdoor",
        description=SensorEntityDescription(
            key="errorCode",
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatSyncCoordinator = entry.runtime_data

    # Find one address per type. Most installs have one indoor + one
    # outdoor; multi-IDU systems would extend this.
    indoor  = next((a for a, d in coordinator.data.items() if d.get("type") == "indoor"), None)
    outdoor = next((a for a, d in coordinator.data.items() if d.get("type") == "outdoor"), None)

    entities: list[HeatSyncSensor] = []
    if indoor:
        for s in INDOOR_SENSORS:
            entities.append(HeatSyncSensor(coordinator, indoor, s))
    if outdoor:
        for s in OUTDOOR_SENSORS:
            entities.append(HeatSyncSensor(coordinator, outdoor, s))
    async_add_entities(entities)


class HeatSyncSensor(HeatSyncEntity, SensorEntity):
    def __init__(
        self,
        coordinator: HeatSyncCoordinator,
        address: str,
        definition: HSSensorDef,
    ) -> None:
        super().__init__(coordinator, address)
        self._def = definition
        self.entity_description = definition.description
        self._attr_name = definition.name
        self._attr_unique_id = (
            f"{coordinator.entry.unique_id}_{address}_{definition.field}"
        )

    @property
    def native_value(self) -> Any:
        return self.device.get(self._def.field)

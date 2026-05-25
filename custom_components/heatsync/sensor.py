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
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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
    _t("Flow target",       "flowTarget",   "indoor"),
    _t("Water inlet",       "waterInlet",   "indoor"),
    _t("Water-law target",  "waterLawTarget","indoor"),
    _t("Water-law offset",  "waterLawOffset","indoor"),
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
    HSSensorDef(
        name="Pump PWM", field="pumpPwm", device_type="indoor",
        description=SensorEntityDescription(
            key="pumpPwm",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
        ),
    ),
    HSSensorDef(
        name="EEV (indoor)", field="eevIndoor", device_type="indoor",
        description=SensorEntityDescription(
            key="eevIndoor",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,   # refrigerant detail, off by default
        ),
    ),
]

# Outdoor-unit sensors (10.xx.xx) — the electrical + compressor side.
OUTDOOR_SENSORS: list[HSSensorDef] = [
    _t("Outdoor temp",    "outdoorTemp",     "outdoor"),
    _t("Discharge temp",  "dischargeTemp",   "outdoor"),
    _t("Suction temp",    "suctionTemp",     "outdoor"),
    _t("High sat temp",   "highSatTemp",     "outdoor"),
    _t("Low sat temp",    "lowSatTemp",      "outdoor"),
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
        name="Compressor freq target", field="compFreqTarget", device_type="outdoor",
        description=SensorEntityDescription(
            key="compFreqTarget",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfFrequency.HERTZ,
            entity_registry_enabled_default=False,   # diagnostic, off by default
        ),
    ),
    HSSensorDef(
        name="EEV (outdoor)", field="eevMain", device_type="outdoor",
        description=SensorEntityDescription(
            key="eevMain",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
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

    entities: list[SensorEntity] = []
    if indoor:
        for s in INDOOR_SENSORS:
            entities.append(HeatSyncSensor(coordinator, indoor, s))
    if outdoor:
        for s in OUTDOOR_SENSORS:
            entities.append(HeatSyncSensor(coordinator, outdoor, s))

    # System-health entities — chip temp, WiFi quality, heap, uptime.
    # Source: /api/diagnose system block (polled every 30 s by the
    # coordinator). Independent of NASA bus state — work even if the
    # bus is offline.
    entities.extend([
        ChipTempSensor(coordinator),
        WifiQualitySensor(coordinator),
        WifiRssiSensor(coordinator),
        HeapFreeSensor(coordinator),
        HeapLargestSensor(coordinator),
        UptimeSensor(coordinator),
    ])

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


# ── System-health sensors (source: /api/diagnose system block) ────────
# Each reads from `coordinator.system_data` rather than per-device
# `coordinator.data[address]`. They live on the HeatSync HA device
# card the same way as bus entities — same identifiers, just no NASA
# address binding.

class _SystemSensorBase(SensorEntity):
    """Base for entities that read coordinator.system_data."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        self._coordinator = coordinator
        # Same device identifiers as the bus entities (see entity.py)
        # so all entities cluster under one HeatSync card in HA.
        from homeassistant.helpers.device_registry import DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or "unknown")},
        )

    @property
    def available(self) -> bool:
        # Only "available" once the first /api/diagnose poll has landed.
        return bool(self._coordinator.system_data)

    async def async_added_to_hass(self) -> None:
        # Subscribe to coordinator updates so HA refreshes us when new
        # /api/diagnose data lands.
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )


class ChipTempSensor(_SystemSensorBase):
    _attr_name = "Chip temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:thermometer-chevron-up"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_chip_temp"

    @property
    def native_value(self) -> float | None:
        return self._coordinator.system_data.get("chipTempC")


class WifiRssiSensor(_SystemSensorBase):
    """Raw dBm reading — for users who want the engineering value.
    Default-disabled in favour of the percentage version below."""
    _attr_name = "WiFi RSSI"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_wifi_rssi"

    @property
    def native_value(self) -> int | None:
        v = self._coordinator.system_data.get("wifiRssi")
        return int(v) if v is not None else None


class WifiQualitySensor(_SystemSensorBase):
    """WiFi signal as 0-100 %. Standard linear conversion:
       -50 dBm → 100 %, -100 dBm → 0 %, linear between.
       More intuitive than raw dBm; default-enabled."""
    _attr_name = "WiFi signal"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_wifi_quality"

    @property
    def native_value(self) -> int | None:
        v = self._coordinator.system_data.get("wifiRssi")
        if v is None:
            return None
        rssi = int(v)
        if rssi >= -50:
            return 100
        if rssi <= -100:
            return 0
        return 2 * (rssi + 100)


class HeapFreeSensor(_SystemSensorBase):
    _attr_name = "Heap free"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "B"
    _attr_icon = "mdi:memory"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_heap_free"

    @property
    def native_value(self) -> int | None:
        v = self._coordinator.system_data.get("heapFree")
        return int(v) if v is not None else None


class HeapLargestSensor(_SystemSensorBase):
    _attr_name = "Heap largest block"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "B"
    _attr_icon = "mdi:memory"
    _attr_entity_registry_enabled_default = False  # diagnostic, opt-in

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_heap_largest"

    @property
    def native_value(self) -> int | None:
        v = self._coordinator.system_data.get("heapLargestBlock")
        return int(v) if v is not None else None


class UptimeSensor(_SystemSensorBase):
    _attr_name = "Uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_uptime"

    @property
    def native_value(self) -> int | None:
        v = self._coordinator.system_data.get("uptimeSec")
        return int(v) if v is not None else None

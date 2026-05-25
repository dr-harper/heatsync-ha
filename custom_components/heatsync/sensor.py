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

    # Derived-totals entities — today's kWh / pence / carbon. Source:
    # /api/cost/status + /api/carbon/status (polled every 60 s by the
    # coordinator). The firmware does the integration; we just surface
    # the running totals as proper HA energy/cost/carbon sensors.
    entities.extend([
        EnergyTodaySensor(coordinator),
        EnergyTodayHeatingSensor(coordinator),
        EnergyTodayDhwSensor(coordinator),
        EnergyTodayDefrostSensor(coordinator),
        EnergyTodayStandbySensor(coordinator),
        CostTodaySensor(coordinator),
        TariffRateNowSensor(coordinator),
        TariffBucketSensor(coordinator),
        CarbonIntensityNowSensor(coordinator),
        # Yesterday cluster — stable daily summaries from /api/energy/daily.
        # COP-yesterday is enabled by default (it's the headline KPI);
        # the rest are entity_registry_enabled_default=False so they
        # don't clutter the device card unless the user opts in.
        EnergyYesterdaySensor(coordinator),
        EnergyYesterdayThermalSensor(coordinator),
        CopYesterdaySensor(coordinator),
        OutdoorAvgYesterdaySensor(coordinator),
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


# ── Derived-totals sensors (source: /api/cost/status + /api/carbon/status)
# These mirror the system-health pattern: not bound to a NASA bus address,
# clustered under the HeatSync device card, refreshed on coordinator
# updates. Backing dict is `coordinator.extras_data` with keys
# {"cost": {…}, "carbon": {…}} populated every EXTRAS_INTERVAL_SEC.
#
# A note on `total_increasing`: HA expects the value to monotonically rise
# until it resets at a known boundary (here: midnight, when the firmware
# rolls today's counters to 0). HA detects a downwards step as a reset
# and starts a new period — that's how the Energy Dashboard knows to
# bucket consumption per day. Don't switch to `total` or it'll double-
# count across the rollover.

class _ExtrasSensorBase(SensorEntity):
    """Base for entities that read coordinator.extras_data.

    Subclasses set their own _attr_unique_id and override `native_value`
    to pull from either the "cost" or "carbon" sub-blob. `_subkey` picks
    which one for the availability gate so a sensor whose source endpoint
    failed shows Unavailable rather than reporting stale data.
    """
    _attr_has_entity_name = True
    _subkey: str = "cost"   # "cost" or "carbon"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        self._coordinator = coordinator
        from homeassistant.helpers.device_registry import DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or "unknown")},
        )

    @property
    def available(self) -> bool:
        return bool(self._coordinator.extras_data.get(self._subkey))

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    def _cost(self) -> dict[str, Any]:
        return self._coordinator.extras_data.get("cost") or {}

    def _carbon(self) -> dict[str, Any]:
        return self._coordinator.extras_data.get("carbon") or {}


class EnergyTodaySensor(_ExtrasSensorBase):
    """Total electrical kWh consumed today (peak + off-peak buckets)."""
    _attr_name = "Energy today"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_energy_today"

    @property
    def native_value(self) -> float | None:
        c = self._cost()
        p = c.get("peakKwh")
        o = c.get("offPeakKwh")
        if p is None and o is None:
            return None
        return round(float(p or 0) + float(o or 0), 3)


def _mode_kwh(c: dict[str, Any], mode: str) -> float | None:
    """Sum peak + off-peak for one mode bucket, returning None if absent."""
    p = c.get(f"{mode}PeakKwh")
    o = c.get(f"{mode}OffPeakKwh")
    if p is None and o is None:
        # Fall back to legacy `<mode>Kwh` (older firmware)
        v = c.get(f"{mode}Kwh")
        return float(v) if v is not None else None
    return round(float(p or 0) + float(o or 0), 3)


class _ModeEnergySensor(_ExtrasSensorBase):
    """Shared body for the per-mode today-kWh sensors. Subclass picks a
    `_mode` key matching the firmware's bucket names (heating, dhw,
    defrost, standby) and a display name + icon."""
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_entity_registry_enabled_default = False   # opt-in detail
    _mode: str = "heating"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_energy_today_{self._mode}"

    @property
    def native_value(self) -> float | None:
        return _mode_kwh(self._cost(), self._mode)


class EnergyTodayHeatingSensor(_ModeEnergySensor):
    _mode = "heating"
    _attr_name = "Energy today (heating)"
    _attr_icon = "mdi:radiator"


class EnergyTodayDhwSensor(_ModeEnergySensor):
    _mode = "dhw"
    _attr_name = "Energy today (hot water)"
    _attr_icon = "mdi:water-boiler"


class EnergyTodayDefrostSensor(_ModeEnergySensor):
    _mode = "defrost"
    _attr_name = "Energy today (defrost)"
    _attr_icon = "mdi:snowflake-melt"


class EnergyTodayStandbySensor(_ModeEnergySensor):
    _mode = "standby"
    _attr_name = "Energy today (standby)"
    _attr_icon = "mdi:power-sleep"


class CostTodaySensor(_ExtrasSensorBase):
    """Today's running cost — converted from pence to pounds for the
    Energy Dashboard's monetary device-class.

    The Dashboard's running-cost tile expects GBP-denominated totals
    that reset at midnight, which is exactly what the firmware's
    `todayPence` is. Dividing by 100 here puts it in the unit HA's
    monetary device-class expects."""
    _attr_name = "Cost today"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "GBP"
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_cost_today"

    @property
    def native_value(self) -> float | None:
        v = self._cost().get("todayPence")
        return round(float(v) / 100.0, 2) if v is not None else None


class TariffRateNowSensor(_ExtrasSensorBase):
    """Current tariff rate £/kWh. Reflects the device's peak/off-peak
    schedule — moves at the boundary times (e.g. 00:30 / 04:30 for
    Octopus Go)."""
    _attr_name = "Tariff rate"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "GBP/kWh"
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:cash-clock"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_tariff_rate_now"

    @property
    def native_value(self) -> float | None:
        v = self._cost().get("rateNowPence")
        return round(float(v) / 100.0, 4) if v is not None else None


class TariffBucketSensor(_ExtrasSensorBase):
    """Which tariff bucket is active right now: 'peak' or 'offPeak'.
    Handy for automations like "only run dishwasher when bucket=offPeak"."""
    _attr_name = "Tariff bucket"
    _attr_icon = "mdi:tag-outline"
    _attr_translation_key = "tariff_bucket"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_tariff_bucket"

    @property
    def native_value(self) -> str | None:
        return self._cost().get("bucket")


class CarbonIntensityNowSensor(_ExtrasSensorBase):
    """Current grid carbon intensity (gCO₂/kWh) for the user's
    configured region. Source: carbonintensity.org.uk via the firmware's
    carbon tracker. Updates every 30 min as the API refreshes."""
    _attr_name = "Carbon intensity"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "gCO2/kWh"
    _attr_icon = "mdi:molecule-co2"
    _subkey = "carbon"

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_carbon_intensity_now"

    @property
    def native_value(self) -> int | None:
        v = self._carbon().get("currentG")
        return int(v) if v is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self._carbon()
        return {
            "region": c.get("region"),
            "postcode": c.get("postcode"),
        }


# ── Yesterday cluster (source: /api/energy/daily, most-recent past day) ──
# These read from a third throttled fetch (hourly) since historical day
# rows don't change once the day rolls over. Useful as stable daily
# summaries for energy dashboards and Tesla-style "yesterday's COP" tiles.

class _YesterdaySensorBase(SensorEntity):
    """Base for sensors that read the most-recent entry of
    `coordinator.extras_data['daily']['days']` (i.e. yesterday)."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        self._coordinator = coordinator
        from homeassistant.helpers.device_registry import DeviceInfo
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or "unknown")},
        )

    @property
    def available(self) -> bool:
        return self._yesterday() is not None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    def _yesterday(self) -> dict[str, Any] | None:
        # The firmware emits `days` oldest-first, current day appended last.
        # "Yesterday" is therefore the second-to-last entry (-2). The last
        # entry (-1) is partial today which would skew "daily summary"
        # behaviour, so we deliberately avoid it.
        daily = self._coordinator.extras_data.get("daily") or {}
        days = daily.get("days") or []
        return days[-2] if len(days) >= 2 else None


class EnergyYesterdaySensor(_YesterdaySensorBase):
    _attr_name = "Energy yesterday"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_energy_yesterday"

    @property
    def native_value(self) -> float | None:
        y = self._yesterday()
        v = y.get("kwhElec") if y else None
        return round(float(v), 2) if v is not None else None


class EnergyYesterdayThermalSensor(_YesterdaySensorBase):
    _attr_name = "Energy yesterday (thermal)"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:fire"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_energy_yesterday_thermal"

    @property
    def native_value(self) -> float | None:
        y = self._yesterday()
        v = y.get("kwhThermal") if y else None
        return round(float(v), 2) if v is not None else None


class CopYesterdaySensor(_YesterdaySensorBase):
    """Yesterday's whole-day COP — the most-useful single efficiency
    metric for owners. Defrost dips and morning warm-ups don't matter
    once you look at the full day."""
    _attr_name = "COP yesterday"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-pump"
    _attr_suggested_display_precision = 2
    _attr_entity_category = None  # promote to "main" view, not diagnostic

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_cop_yesterday"

    @property
    def native_value(self) -> float | None:
        y = self._yesterday()
        if not y:
            return None
        elec = y.get("kwhElec")
        therm = y.get("kwhThermal")
        if not elec or not therm or float(elec) <= 0:
            return None
        return round(float(therm) / float(elec), 2)


class OutdoorAvgYesterdaySensor(_YesterdaySensorBase):
    _attr_name = "Outdoor temp yesterday (avg)"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: HeatSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_outdoor_avg_yesterday"

    @property
    def native_value(self) -> float | None:
        y = self._yesterday()
        v = y.get("outdoorAvg") if y else None
        return float(v) if v is not None else None

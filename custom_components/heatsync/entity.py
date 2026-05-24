"""Base entity for HeatSync.

All HeatSync entities inherit from HeatSyncEntity. It wires up the
DataUpdateCoordinator subscription and supplies the `device_info`
block so HA groups every entity under one device card (matching the
firmware's MQTT-side grouping).
"""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HeatSyncCoordinator


class HeatSyncEntity(CoordinatorEntity[HeatSyncCoordinator]):
    """Base class — every platform entity inherits this.

    `address` is the NASA bus address ("20.00.00" indoor, "10.00.00"
    outdoor) the entity reads its state from. CoordinatorEntity wires
    up subscription so HA's state machine updates automatically when
    the coordinator polls.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HeatSyncCoordinator,
        address: str,
    ) -> None:
        super().__init__(coordinator)
        self._address = address
        # Single device card for the whole controller — same `identifiers`
        # as the firmware's MQTT discovery uses. unique_id on each entity
        # combines DOMAIN, the entry's unique_id, and a field suffix.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or "unknown")},
            name="HeatSync",
            manufacturer="Samsung",
            model="NASA Heat Pump",
            configuration_url=f"http://{coordinator.entry.data['host']}",
        )

    @property
    def device(self) -> dict[str, Any]:
        """The /api/live blob for this entity's NASA address."""
        return self.coordinator.data.get(self._address, {})

    @property
    def available(self) -> bool:
        """Available when the coordinator's last update succeeded AND
        the address we care about was in the response."""
        return self.coordinator.last_update_success and bool(self.device)

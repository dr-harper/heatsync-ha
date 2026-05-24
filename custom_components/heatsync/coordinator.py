"""DataUpdateCoordinator for HeatSync.

One coordinator per config entry. Polls /api/live every UPDATE_INTERVAL,
parses the {"devices": [...]} response into a flat dict keyed by NASA
bus address, and notifies all subscribed entities.

This is the idiomatic HA pattern (the "Gold-standard" quality tier
explicitly recommends DataUpdateCoordinator). It means:
  • One HTTP request per refresh interval, regardless of entity count
  • Entities just declare what they care about via `coordinator.data`
  • Auth failures bubble up to trigger a reauth flow
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import HeatSyncAuthError, HeatSyncClient, HeatSyncConnectionError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HeatSyncCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Shared poller for the integration's HTTP API.

    `data` is a dict keyed by NASA bus address (e.g. "20.00.00") whose
    values are the per-device JSON blobs from /api/live. Entities look
    up their address in the dict to find their fields.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: HeatSyncClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry.data['host']})",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            raw = await self.client.live()
        except HeatSyncAuthError as exc:
            # Bubble up to HA so the user sees a "Reauthenticate"
            # action in the Devices & Services UI.
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except HeatSyncConnectionError as exc:
            # Transient — coordinator marks data stale, retries next
            # interval. Entities will show as Unavailable until success.
            raise UpdateFailed(str(exc)) from exc

        devices = raw.get("devices") or []
        return {dev.get("address"): dev for dev in devices if dev.get("address")}

"""DataUpdateCoordinator for HeatSync.

One coordinator per config entry. Polls /api/live every UPDATE_INTERVAL,
parses the {"devices": [...]} response into a flat dict keyed by NASA
bus address, and notifies all subscribed entities. Also polls
/api/diagnose at a slower cadence (DIAGNOSE_INTERVAL) to surface
device-health metrics — chip temperature, WiFi RSSI, heap stats — that
aren't on the bus.

This is the idiomatic HA pattern (the "Gold-standard" quality tier
explicitly recommends DataUpdateCoordinator). It means:
  • One HTTP request per refresh interval, regardless of entity count
  • Entities just declare what they care about via `coordinator.data`
    (NASA bus state) or `coordinator.system_data` (diag snapshot)
  • Auth failures bubble up to trigger a reauth flow
"""
from __future__ import annotations

import logging
import time
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

# /api/diagnose is heavier than /api/live (full system snapshot, ~4 KB
# JSON). The device-health values it carries don't need 5-s refresh —
# heap, uptime, chip temp, WiFi RSSI move slowly. Poll every 30 s.
DIAGNOSE_INTERVAL_SEC = 30

# Derived totals (/api/cost/status + /api/carbon/status). Today's running
# kWh / pence / gCO₂ move slowly enough — running averages over a day —
# that minute-level cadence is plenty. Polling slower than this also
# keeps the firmware's HTTPS budget for weather + carbon fetches free.
EXTRAS_INTERVAL_SEC = 60

# /api/energy/daily is historical (one entry per past day), only moves at
# the midnight roll-over. Polling once an hour is generous — even daily
# would be fine — but an hourly cadence keeps the "Yesterday" sensors
# fresh shortly after midnight even if the user happens to be looking.
DAILY_INTERVAL_SEC = 3600


class HeatSyncCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Shared poller for the integration's HTTP API.

    `data` is a dict keyed by NASA bus address (e.g. "20.00.00") whose
    values are the per-device JSON blobs from /api/live. Entities look
    up their address in the dict to find their fields.

    `system_data` is a separate dict carrying the /api/diagnose
    `system` block — fw version, uptime, heap, chip temp, WiFi RSSI,
    etc. Updated every DIAGNOSE_INTERVAL_SEC (independent of the
    main coordinator's update_interval). Read directly by the
    system-health sensor entities.
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
        # System-health snapshot from /api/diagnose. Empty until the
        # first throttled fetch lands; system sensors read None until
        # then which surfaces as Unavailable in HA — correct behaviour.
        self.system_data: dict[str, Any] = {}
        self._last_diag_at = 0.0
        # Derived totals — today's kWh / pence / carbon. Merged blob:
        #   {"cost": {…/api/cost/status…}, "carbon": {…/api/carbon/status…}}
        # Lives under one dict so all the derived-sensor entities share
        # a single "did the throttled fetch succeed yet?" availability
        # signal. Empty until the first 60-s tick lands.
        self.extras_data: dict[str, Any] = {}
        self._last_extras_at = 0.0
        self._last_daily_at = 0.0

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            raw = await self.client.live()
        except HeatSyncAuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except HeatSyncConnectionError as exc:
            raise UpdateFailed(str(exc)) from exc

        # Throttled /api/diagnose fetch — runs once every
        # DIAGNOSE_INTERVAL_SEC, piggy-backing on whichever main poll
        # crosses the threshold. Failures here are non-fatal: we keep
        # the previous system snapshot rather than blocking the whole
        # refresh cycle (live data is more critical than diag data).
        now = time.monotonic()
        if now - self._last_diag_at >= DIAGNOSE_INTERVAL_SEC:
            self._last_diag_at = now
            try:
                diag = await self.client.diagnose()
                self.system_data = diag.get("system") or {}
            except (HeatSyncConnectionError, HeatSyncAuthError):
                # Keep the previous snapshot. Entities show Unavailable
                # only if we never managed a first fetch.
                pass

        # Throttled extras fetch — cost + carbon, both small JSON blobs.
        # Same failure semantics as diagnose: a single endpoint failing
        # leaves the prior value visible rather than dropping all the
        # derived sensors to Unavailable in lockstep.
        if now - self._last_extras_at >= EXTRAS_INTERVAL_SEC:
            self._last_extras_at = now
            extras: dict[str, Any] = dict(self.extras_data)  # copy-on-write
            try:
                extras["cost"] = await self.client.cost_status()
            except (HeatSyncConnectionError, HeatSyncAuthError):
                pass
            try:
                extras["carbon"] = await self.client.carbon_status()
            except (HeatSyncConnectionError, HeatSyncAuthError):
                pass
            self.extras_data = extras

        # /api/energy/daily — hourly cadence, see DAILY_INTERVAL_SEC.
        # Stashed under extras_data["daily"] so the yesterday-cluster
        # sensors share a single fetch + availability gate.
        if now - self._last_daily_at >= DAILY_INTERVAL_SEC:
            self._last_daily_at = now
            try:
                daily = await self.client.energy_daily()
                self.extras_data = {**self.extras_data, "daily": daily}
            except (HeatSyncConnectionError, HeatSyncAuthError):
                pass

        devices = raw.get("devices") or []
        return {dev.get("address"): dev for dev in devices if dev.get("address")}

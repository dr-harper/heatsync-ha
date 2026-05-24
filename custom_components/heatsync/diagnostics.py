"""Diagnostics export for HA's downloadable-bug-report feature.

When a user clicks 'Download Diagnostics' in HA's UI for a HeatSync
config entry, this builds a redacted JSON blob containing everything
useful for filing an issue: device's /api/diagnose snapshot + the
coordinator's last-known state, minus the bearer token.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from .api import HeatSyncConnectionError
from .coordinator import HeatSyncCoordinator

# Redact the bearer token AND the token field if surfaced anywhere
# else (host MAC, postcode, etc. are kept — they're not secret).
REDACT_KEYS = {CONF_TOKEN, "token", "apiToken"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    coordinator: HeatSyncCoordinator = entry.runtime_data

    out: dict[str, Any] = {
        "entry": async_redact_data(dict(entry.data), REDACT_KEYS),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "data": coordinator.data,
        },
    }
    # Best-effort device snapshot — if the device's busy, omit rather
    # than fail the whole diagnostics export.
    try:
        out["device_diagnose"] = await coordinator.client.diagnose()
    except HeatSyncConnectionError as exc:
        out["device_diagnose_error"] = str(exc)

    return out

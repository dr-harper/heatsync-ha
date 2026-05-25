"""The HeatSync integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatSyncClient
from .const import PLATFORMS
from .coordinator import HeatSyncCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatSync from a config entry.

    Creates the API client, builds the coordinator, runs the first
    refresh to validate the connection, then forwards platform setup.

    Note: a real-time SSE push path was prototyped but reverted — the
    firmware's 4 MB hardware didn't have the heap headroom for the
    additional WiFiServer + worker tasks. Polling at the coordinator's
    UPDATE_INTERVAL is the supported transport. Sub-second push will
    return when we move to the 8 MB AtomS3.
    """
    session = async_get_clientsession(hass)
    client = HeatSyncClient(session, entry.data[CONF_HOST], entry.data[CONF_TOKEN])

    coordinator = HeatSyncCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry — tear down platforms cleanly."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

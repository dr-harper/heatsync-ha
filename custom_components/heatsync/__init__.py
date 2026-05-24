"""The HeatSync integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatSyncClient
from .const import DOMAIN, PLATFORMS
from .coordinator import HeatSyncCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatSync from a config entry.

    Creates the API client, builds the coordinator, runs the first
    refresh to validate the connection, then forwards platform setup.
    """
    session = async_get_clientsession(hass)
    client = HeatSyncClient(session, entry.data[CONF_HOST], entry.data[CONF_TOKEN])

    coordinator = HeatSyncCoordinator(hass, entry, client)
    # First refresh — if it raises, async_setup_entry returns False and
    # HA shows "Failed to set up". Auth failures become reauth prompts;
    # transport failures become retries.
    await coordinator.async_config_entry_first_refresh()

    # Store on the entry's runtime_data — HA 2024+ idiomatic pattern,
    # avoids the global hass.data[DOMAIN][entry_id] dict.
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry — tear down platforms cleanly."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

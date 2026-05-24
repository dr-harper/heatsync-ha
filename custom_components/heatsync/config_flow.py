"""Config flow for HeatSync.

Two entry paths:
  1. User clicks "Add Integration" → fills host + token by hand
  2. HA's zeroconf discovery picks up the device's mDNS advert
     (heatsync.local) → we ask only for the token

Both paths share `_verify_and_create` which probes /api/status with the
token to confirm we can reach the device before committing the entry.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol  # type: ignore[import-untyped]

from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatSyncAuthError, HeatSyncClient, HeatSyncConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HeatSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        # Populated by the zeroconf path so the form pre-fills the host.
        self._discovered_host: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manual entry — user types host + token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip()
            try:
                return await self._verify_and_create(host, token)
            except HeatSyncAuthError:
                errors["base"] = "invalid_auth"
            except HeatSyncConnectionError:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=self._discovered_host or "heatsync.local",
                ): str,
                vol.Required(CONF_TOKEN): str,
            },
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "token_help": (
                    "Generate a token in the HeatSync device's web UI: "
                    "Settings → API token → Generate."
                ),
            },
        )

    async def async_step_zeroconf(
        self,
        discovery_info: zeroconf.ZeroconfServiceInfo,
    ) -> ConfigFlowResult:
        """mDNS auto-discovery — HA found heatsync.local on the network."""
        host = discovery_info.host
        # The device's mDNS name is "heatsync_XXXXXX.local" where XXXXXX
        # is the chip-id suffix. We use that suffix as the unique_id so
        # multiple devices on the same LAN don't collide.
        chip_id = discovery_info.name.removeprefix("heatsync_").split(".")[0]
        await self.async_set_unique_id(f"heatsync_{chip_id}")
        # Update the entry if the device's IP changed (DHCP).
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovered_host = host
        self.context["title_placeholders"] = {"name": f"HeatSync ({host})"}
        return await self.async_step_user()

    async def _verify_and_create(self, host: str, token: str) -> ConfigFlowResult:
        """Common path: probe /api/status, then commit the entry."""
        session = async_get_clientsession(self.hass)
        client = HeatSyncClient(session, host, token)
        # Raises HeatSyncAuthError on bad token, HeatSyncConnectionError
        # on timeout / refused — both surface as errors in the form.
        status = await client.status()

        # Use the device's chipId (from /api/status if exposed, otherwise
        # the host string) as the unique identifier so re-adding the
        # same device dedupes instead of creating a duplicate entry.
        chip_id = status.get("chipId") or host
        await self.async_set_unique_id(f"heatsync_{chip_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"HeatSync ({host})",
            data={CONF_HOST: host, CONF_TOKEN: token},
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Triggered when the coordinator hits HeatSyncAuthError.

        Shows the user a form to enter a fresh token (host is unchanged).
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        host = entry.data[CONF_HOST]

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            try:
                await HeatSyncClient(session, host, token).status()
            except HeatSyncAuthError:
                errors["base"] = "invalid_auth"
            except HeatSyncConnectionError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_TOKEN: token},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
            description_placeholders={"host": host},
        )

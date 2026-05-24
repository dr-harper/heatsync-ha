"""Smoke test: integration boots from a mocked config entry.

This catches the most common breakage class: HA changes a base-class
signature and our async_setup_entry stops importing. The fuller
test suite (config flow, entity behaviour, error paths) is a roadmap
item — gold-standard would have ≥80 % coverage.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.heatsync.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_entry_smoke(hass: HomeAssistant) -> None:
    """Sets up an entry with a mocked API client; expects LOADED state."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="heatsync_test",
        data={"host": "heatsync.local", "token": "x" * 32},
    )
    entry.add_to_hass(hass)

    sample_live = {
        "devices": [
            {
                "address": "20.00.00",
                "type": "indoor",
                "mode": "heat",
                "power": True,
                "roomTemp": 21.5,
                "targetTemp": 22.0,
                "dhwPower": True,
                "dhwMode": "standard",
                "dhwTarget": 50,
                "tankTemp": 48.2,
                "waterLawOffset": 0.0,
            },
            {
                "address": "10.00.00",
                "type": "outdoor",
                "outdoorTemp": 12.3,
                "powerW": 0,
                "compFreq": 0,
                "errorCode": 0,
                "fault": False,
            },
        ],
    }

    with patch(
        "custom_components.heatsync.api.HeatSyncClient.live",
        new=AsyncMock(return_value=sample_live),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

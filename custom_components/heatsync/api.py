"""Async HTTP client for the HeatSync device.

Wraps the device's /api/* endpoints. All calls are async via aiohttp.
The device uses a Bearer-token scheme (generated in the device's
Settings → API token UI) — the same token is used for every call.

The client is intentionally small: one method per device endpoint we
actually need. Adding new endpoints means adding new methods, not
threading a generic call through string args.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ClientError

from .const import HTTP_TIMEOUT_SEC

_LOGGER = logging.getLogger(__name__)


class HeatSyncAuthError(Exception):
    """Bearer token rejected. Surfaced as a reauth flow in HA."""


class HeatSyncConnectionError(Exception):
    """Network-level failure (timeout, refused, DNS). Transient — coordinator
    treats this as a poll miss, retries on the next interval."""


class HeatSyncClient:
    """Thin async wrapper around the device's HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        token: str,
    ) -> None:
        self._session = session
        self._host = host
        self._token = token
        self._base = f"http://{host}"
        self._headers = {"Authorization": f"Bearer {token}"}

    # ── Health probe: /api/status ───────────────────────────────────────
    # Used by the config flow to verify host + token before we commit
    # the entry. Returns a small dict — version, uptime, etc.
    async def status(self) -> dict[str, Any]:
        return await self._get("/api/status")

    # ── Main state poll: /api/live ──────────────────────────────────────
    # Returns {"devices": [...]} with one entry per NASA address.
    # The DataUpdateCoordinator hits this every UPDATE_INTERVAL.
    async def live(self) -> dict[str, Any]:
        return await self._get("/api/live")

    # ── Diagnostics snapshot: /api/diagnose ────────────────────────────
    # Used by HA's diagnostics-export feature. Includes system info,
    # bus stats, mqtt state, events log — everything needed to file a
    # useful bug report.
    async def diagnose(self) -> dict[str, Any]:
        return await self._get("/api/diagnose")

    # ── Derived totals: cost / carbon / daily energy ────────────────────
    # All three are firmware-computed running totals — the device tracks
    # elec consumption per tariff bucket, integrates power * intensity,
    # and persists daily totals across midnight. The coordinator polls
    # these on a slower cadence (60 s) than /api/live; they don't move
    # fast enough to justify 5-s refresh.
    async def cost_status(self) -> dict[str, Any]:
        return await self._get("/api/cost/status")

    async def carbon_status(self) -> dict[str, Any]:
        return await self._get("/api/carbon/status")

    async def energy_daily(self) -> dict[str, Any]:
        return await self._get("/api/energy/daily")

    # ── Control surface: /api/control/* (POST) ─────────────────────────
    # These mirror the buttons/sliders on the device's own dashboard.
    # Each takes its bounds-checked params and POSTs as form data.
    async def set_water_law_offset(self, value: float) -> None:
        await self._post_form("/api/control/water-law-offset", {"value": str(value)})

    async def set_dhw_target(self, value: float) -> None:
        await self._post("/api/control/dhw-target", params={"value": str(value)})

    async def set_dhw_power(self, on: bool) -> None:
        await self._post("/api/control/dhw-power", params={"on": "1" if on else "0"})

    async def set_dhw_mode(self, mode: str) -> None:
        # Device accepts: eco | standard | power | force (lowercase).
        await self._post("/api/control/dhw-mode", params={"mode": mode})

    async def set_heating_mode(self, mode: str) -> None:
        # heat | cool | auto | off
        await self._post("/api/control/heating-mode", params={"mode": mode})

    async def set_heating_target(self, value: float) -> None:
        await self._post("/api/control/heating-target", params={"value": str(value)})

    async def set_away(self, on: bool) -> None:
        await self._post("/api/control/away", params={"on": "1" if on else "0"})

    async def heating_boost(self) -> None:
        await self._post("/api/control/heating-boost")

    async def dhw_boost(self) -> None:
        await self._post("/api/control/dhw-boost")

    # ── Plumbing ───────────────────────────────────────────────────────
    async def _get(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def _post(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, params=params)

    async def _post_form(
        self,
        path: str,
        data: dict[str, str],
    ) -> dict[str, Any]:
        return await self._request("POST", path, data=data)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        _LOGGER.debug("HTTP %s %s params=%s data=%s", method, url, params, data)
        try:
            async with asyncio.timeout(HTTP_TIMEOUT_SEC):
                async with self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    params=params,
                    data=data,
                ) as resp:
                    if resp.status == 401:
                        raise HeatSyncAuthError(
                            f"Bearer token rejected by {url}",
                        )
                    if resp.status >= 400:
                        raise HeatSyncConnectionError(
                            f"{method} {path} → HTTP {resp.status}",
                        )
                    # Most endpoints return JSON; control endpoints may
                    # return {"ok": true}. Parse defensively.
                    try:
                        return await resp.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError):
                        return {}
        except asyncio.TimeoutError as exc:
            raise HeatSyncConnectionError(
                f"{method} {path} timed out after {HTTP_TIMEOUT_SEC} s",
            ) from exc
        except ClientError as exc:
            raise HeatSyncConnectionError(
                f"{method} {path} failed: {exc}",
            ) from exc

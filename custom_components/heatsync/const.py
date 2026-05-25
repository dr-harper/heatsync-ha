"""Constants for the HeatSync integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "heatsync"

# Config-flow user-input keys (mirrored to the entry's data dict).
CONF_HOST = "host"
CONF_TOKEN = "token"

# How often to poll /api/live. The device's own dashboard polls every
# ~3 s; we go a touch slower (5 s) to be polite about WiFi / bus load.
# 5 s is fast enough for HA UI to feel responsive without trampling
# the device. Sub-second push via SSE was prototyped + reverted (the
# firmware's 4 MB hardware didn't have heap headroom); will return
# when we move to the 8 MB AtomS3.
UPDATE_INTERVAL = timedelta(seconds=5)

# Default port — the device's WebServer always listens on 80.
DEFAULT_PORT = 80

# Connection timeout for each HTTP call. Kept tight because the device
# typically responds in <100 ms on the LAN; anything over a couple of
# seconds means the device is in trouble (TLS handshake competing for
# heap, etc.) and we'd rather report a transient failure than block the
# whole coordinator.
HTTP_TIMEOUT_SEC = 4

# Platforms this integration sets up. Each one gets its own .py module
# (climate.py, water_heater.py, …) following HA's convention.
PLATFORMS = [
    "climate",
    "water_heater",
    "sensor",
    "binary_sensor",
    "switch",
    "number",
    "button",
]

# HeatSync — Home Assistant integration

A Home Assistant custom integration for the [HeatSync](https://github.com/dr-harper/heatsync)
controller — an ESP32-based bridge to Samsung NASA heat pumps.

The integration polls the device's local HTTP API. No MQTT broker
required (though HeatSync also supports MQTT auto-discovery if you
prefer that path).

## What you get

| Entity | Type | Description |
|---|---|---|
| Heat pump | `climate` | Mode (heat/cool/auto/off) + target + current room temp |
| Hot water | `water_heater` | Power + target + mode (eco/standard/power/force) |
| Water-law offset | `number` | ±5 °C heating-curve shift slider |
| Quiet mode, Away | `switch` | Quiet caps compressor max RPM; Away applies setback |
| Heating boost, DHW boost | `button` | One-shot +1 °C / +5 °C for 1 hour |
| Tank temp, Flow actual, Eva in/out, Water inlet, Flow rate, Humidity, Thermal power | `sensor` | Indoor unit |
| Outdoor temp, Discharge / Suction temp, Power, Energy, Current, Voltage, Compressor freq, Fan RPM, Cycles per hour, Error code | `sensor` | Outdoor unit |
| Water pump, Compressor, Fault | `binary_sensor` | Running flags |

All entities sit under a single "HeatSync" device card in HA's UI.

## Install via HACS

1. In HACS → "Integrations" → ⋯ → "Custom repositories"
2. Add `https://github.com/dr-harper/heatsync-ha` as type "Integration"
3. Click "HeatSync" in the integrations list → "Download"
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → "HeatSync"

## Setup

1. **Generate an API token** in the HeatSync device's web UI:
   Settings → API token → Generate. Copy the token.
2. In HA, add the integration. If your device is mDNS-discoverable
   (`heatsync.local`), HA will auto-discover it; otherwise enter the
   host (IP or `.local` name) and paste the token.

## Polling cadence

The integration polls `/api/live` every 5 s. Each entity reads from
the shared poller — adding entities doesn't add HTTP load.

If you want sub-second updates (e.g. for a real-time gauge), pair
this integration with HeatSync's MQTT auto-discovery — the MQTT
topics push as fast as the bus broadcasts (typically 500 ms per
field). Both can coexist; HA will dedupe by `unique_id`.

## Diagnostics

When filing a bug, click "Download diagnostics" on the HeatSync
device card. You'll get a JSON blob with the device's full
`/api/diagnose` snapshot + the coordinator's last-known state, with
the bearer token redacted.

## Quality scale

Currently **Silver** (manifest declared). Climbing to Gold/Platinum
needs: full test coverage, repair flows, multi-language translations,
HA brand-assets submission. Tracked as roadmap items.

## License

MIT.

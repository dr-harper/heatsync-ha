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
| Energy today, Cost today, Tariff rate, Tariff bucket, Carbon intensity | `sensor` | Today's running totals |
| Energy today (heating / hot water / defrost / standby) | `sensor` | Per-mode kWh split — opt-in |
| Energy yesterday, COP yesterday, Outdoor avg yesterday | `sensor` | Yesterday's stable summary |
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

## Two transport paths — pick one

HeatSync gives you two equally-valid ways to surface its data in HA.
**Pick one — running both gives you duplicate entities.**

| | You have an MQTT broker (e.g. HA's Mosquitto add-on) | You don't, or prefer not to |
|---|---|---|
| **Best path** | Skip this integration. Configure MQTT in HeatSync's `/config` page → HA's built-in MQTT integration auto-discovers ~30 entities under one HeatSync device card. Sub-second push (bus broadcast rate). | Install this integration via HACS (steps above). HTTP polling at 5 s, no broker needed. |
| Setup friction | Configure MQTT broker once on both sides | One HACS install + paste a token |
| Latency | < 1 s (push) | ~5 s (poll cadence) |
| Where the entities come from | HA core's MQTT integration | This integration |

The MQTT path is the **HA-idiomatic** way for embedded devices and is
how the firmware was designed first. This integration exists for the
"I don't want to run a broker" crowd. Both ship the same set of
entities — climate, water_heater, sensors, etc.

### Polling cadence (HTTP path)

The integration polls `/api/live` every 5 s. Each entity reads from
the shared poller — adding entities doesn't add HTTP load. Tunable in
`const.py` if 5 s isn't right for your setup.

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

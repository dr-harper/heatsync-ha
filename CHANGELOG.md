# Changelog

All notable changes to the HeatSync Home Assistant integration are
recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] — 25th May 2026

### Features

- **Daily energy, cost and carbon sensors** — surfaces the firmware's
  per-day totals as proper HA sensor entities. Adds:
  - `sensor.energy_today` (kWh, total-increasing) for the Energy Dashboard
  - `sensor.cost_today` (GBP, monetary) for the running-cost tile
  - `sensor.carbon_intensity` (gCO₂/kWh, with region + postcode as
    attributes) sourced from carbonintensity.org.uk via the device
  - `sensor.tariff_rate` (GBP/kWh) and `sensor.tariff_bucket`
    (peak / off-peak) so automations can react to the active band
  - `sensor.energy_today_*` (heating / hot_water / defrost / standby) —
    per-mode kWh split, opt-in (disabled by default to avoid clutter)
- **Yesterday cluster** — stable daily summaries from `/api/energy/daily`:
  - `sensor.cop_yesterday` — the headline efficiency KPI most owners
    actually want (today's COP is noisy until late afternoon)
  - `sensor.energy_yesterday`, `sensor.energy_yesterday_thermal`,
    `sensor.outdoor_temp_yesterday_avg` — opt-in detail

### Internal

- Coordinator now does two throttled fetches alongside the main
  `/api/live` poll: cost + carbon at 60 s, daily energy at 1 h.
  All three failure-isolated — one endpoint down doesn't drag the
  others to Unavailable.
- API client extended with `cost_status()`, `carbon_status()`,
  `energy_daily()`.

## [0.1.0] — earlier

Initial integration release — climate, water heater, sensors,
binary sensors, switches, numbers, buttons.

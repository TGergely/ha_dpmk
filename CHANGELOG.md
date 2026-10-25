# Changelog

All notable changes to this project are listed here. The version number lives only in
`custom_components/dpmk/manifest.json`. While the number starts with 0, new features may still
change how things work.

## 0.2.1 - 2026-10-25

- **Renamed to "Košice Public Transport – DPMK"** (the name Home Assistant and HACS show). The technical
  name `dpmk` is unchanged, so existing installs keep working.
- **Sensor names**: devices are now called `DPMK <stop or place>`, so new sensors get ids like
  `sensor.dpmk_heringes_vysne_opatske_next_departure` or `sensor.dpmk_home_next_departure`. Home Assistant
  never renames an existing entity id by itself: your current sensors keep their ids (and your cards keep
  working), only their device and display names gain the `DPMK` prefix. To get the new id for an existing
  sensor, rename it in its settings (Entity ID), or remove and add the stop again.

- **Every stop now has a position.** The 14 stops that the city's open data lacks (for example Panoráma)
  are placed from OpenStreetMap by `tools/build_stops.py`. Before, a place could never find them.
- Adding a place also offers the stops just **outside** the radius (unticked, with their distance), so a
  stop that is a little too far is one tick away. Only the stops inside the radius are ticked.

## 0.2.0 - 2026-10-25

- **Places**: add several stops near one spot as one place. One sensor, one merged departures list (each
  row says which stop it is from) and one map with all the stops. Stops within a radius are found
  automatically and can be ticked or unticked.
- **The stop list is built in** (`data/stops.json`, 262 stops with positions from the city's open data,
  CC BY 4.0), so adding a stop makes no request to dpmk.sk. When your Home Assistant is in Košice the list
  is sorted by distance. A stop number field covers stops added by DPMK after the list was made.
  `tools/build_stops.py` rebuilds the file.
- **The map centres itself on the stop**; new options: put the map where the stop is, map centre, map
  radius. Existing stops keep the position and radius they had.
- **Default stop or place**: cards without an `entity` use it.
- New option **Language of the cards** (Automatic, Slovak or English); one setting for both cards.
  **Automatic** (follow Home Assistant) is the default. A card's own `language` option still overrides it.
  The time format follows the language.
- The card picker entries are bilingual; the departure line can wrap when a stop name is long.
- Example pictures in the README.

## 0.1.0 - first release

- Choose a DPMK Košice stop by name and add one entry per stop.
- Departures card (`custom:dpmk-departures-card`): line badges in DPMK's colors, destination,
  official time with the real time in brackets, countdown and delay.
- Map card (`custom:dpmk-map-card`): simple gray street map with the buses and trams around the
  stop, green/red ring for arriving/leaving, minutes to the stop.
- Live delays from DPMK's map feed, matched to the exact timetable trip.
- Sensor `sensor.<stop>_next_departure` with the departure and vehicle lists as attributes.
- Options: lines/directions, number of departures, timetable variant, update interval
  (5 to 120 s, default 10 s, the feed is never read more often than every 5 s), vehicles on the
  map (serving this stop or all), stop location and radius.
- Slovak and English; the cards are Slovak by default.
- Integration icon and logo (light and dark) in `brand/` for Home Assistant 2026.3 and newer.

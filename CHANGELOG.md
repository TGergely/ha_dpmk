# Changelog

All notable changes to this project are listed here. The version number lives only in
`custom_components/dpmk/manifest.json`. While the number starts with 0, new features may still
change how things work.

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

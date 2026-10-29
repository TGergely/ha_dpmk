# Changelog

All notable changes to this project are listed here. The version number lives only in
`custom_components/dpmk/manifest.json`. While the number starts with 0, new features may still
change how things work.

## 0.3.0 - 2026-10-29

- **Database**: the sensor's large attributes that change on every refresh (departures, vehicles, stops,
  lines) are no longer recorded. Before, each sensor added roughly 20-30 MB a day to the Home Assistant
  database, and a big place with many vehicles could pass the 16 KB limit above which attributes are not
  stored at all. The state (the next departure) is still recorded.
- **Timetable reload is safe**: if DPMK fails part-way through the 12-hourly reload, a stop that failed
  keeps its previous timetable (before, the timetable could shrink to a few routes for 12 hours). After a
  failure the load is retried after 5 minutes, then 10, 20 and so on up to an hour, and refreshes during
  that pause make no timetable requests. If DPMK is down at start-up, only the first attempt hits the site.
- **Departures card** redraws only when its sensor, the language or the entity changes, not on every state
  change of every entity in Home Assistant.
- **Cards say "DPMK data is unavailable"** when the sensor is unavailable, instead of "No upcoming
  departures" or "No vehicles within range". The map card also shows its message for a missing entity.
- **Map tiles** are requested without a referrer, so the address of your Home Assistant is not sent to the
  tile server.
- **Faster refreshes**: the schedule is sorted once and each refresh only looks at the departures around
  the current time, instead of expanding every trip of every day type. A refresh is roughly 6-11 times
  faster, which matters for a place with many stops. The result is identical to the old method (checked
  against it on random timetables, both clock changes and public holidays).
- **Timetables are kept on disk**: a restart or a change of options no longer downloads hundreds of pages
  again; the saved copy is used straight away (also when dpmk.sk is down) and renewed in the background
  when it is more than 12 hours old. Changing the line filter reuses it as well. The file is deleted when
  the entry is removed.
- **Timetable reloads run in the background**, so the live data keeps refreshing while they are fetched.
- **Fewer requests at night**: while no vehicle of yours is running or nearby and the next departure is
  20 minutes or more away, the sensor refreshes once a minute at most; it returns to your chosen interval
  as soon as something is due.
- **Easier to read without colour**: a vehicle that is leaving has a dashed outline and one that is
  arriving a solid ring (the legend shows both); departures, vehicles, stops and the map have spoken
  labels for screen readers.
- **Safer cards**: all text from the sensor (stop names, destinations, colours) is escaped before it is
  shown, and the card title is set as plain text.
- Removed an unused function from the DPMK client.
- **Logbook**: the next-departure sensor changes state every time its departure passes, which fills the
  Logbook. To hide it, exclude the sensor (see the README, "Good to know").

## 0.2.2 - 2026-10-29

- The README's pictures and links use full web addresses, so they also show inside HACS in Home Assistant
  (HACS displays the README itself, where a relative path like `docs/images/...` points nowhere). The
  screenshots are in a plain Markdown table.

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

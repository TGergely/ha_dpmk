<img src="https://raw.githubusercontent.com/TGergely/ha_dpmk/main/custom_components/dpmk/brand/icon@2x.png" alt="Košice Public Transport – DPMK" width="120" align="right">

# Košice Public Transport – DPMK for Home Assistant

[![Add as a custom repository in HACS](https://img.shields.io/badge/HACS-Custom%20repository-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Pick a bus or tram stop in Košice and see **which line arrives when**, with **live delays**, plus a small **map of the vehicles around your stop**. Everything is shown on two Lovelace cards that come with the integration.

Slovak and English. By default the language is automatic: Slovak when Home Assistant is set to Slovak, English otherwise. You can change it in one place: **Configure → Language of the cards** (Automatic, Slovak or English).

**Install in two clicks** (needs [HACS](https://hacs.xyz) and the [My Home Assistant](https://my.home-assistant.io) link set up once):

1. [![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TGergely&repository=ha_dpmk&category=integration) then download it in HACS and restart Home Assistant.
2. [![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dpmk) to add your first stop. It works only after step 1 **and a restart of Home Assistant**. Before that Home Assistant shows "This integration does not support configuration via the UI", because it does not know the integration yet. You can always use **Settings → Devices & services → Add integration → DPMK Košice** instead.

> Unofficial. Not affiliated with DPMK, a.s. It reads DPMK's public website, which could change without notice.

## What you get

- **Departures card** (`custom:dpmk-departures-card`): line badge in DPMK's official colors (square = bus, circle = tram), destination, the official timetable time and, in brackets, the real time from the live data, plus a countdown and the delay.
- **Map card** (`custom:dpmk-map-card`): a simple, non-interactive picture. A plain gray street map with your stop in the middle and the buses and trams around it. A green ring means the vehicle is arriving at your stop, red means it is leaving, and the label shows the live minutes to your stop.
- **Places**: add several stops near one spot (for example your home) as **one place**. You get one sensor, one departures list that says which stop each departure is from, and one map with all the stops on it.
- **Stop list built in**: all 262 DPMK stops, with their positions, come with the integration. Adding a stop needs no request to dpmk.sk, and the map centres itself on the stop.
- **Default stop**: mark one stop or place as the default, and cards without an `entity` use it.
- **Sensor** `sensor.dpmk_<stop>_next_departure` (timestamp of the next departure) whose attributes hold the whole departure and vehicle lists, for your own templates and automations.
- No account, no API key, no extra Python packages.

## Screenshots

Dark theme, live data. The left column is a **place** called "Home" with five stops in the centre of Košice; the right column is a **single stop** (Slovak texts, because the language follows Home Assistant).

| Place: map | Single stop: map |
|---|---|
| ![Map card of a place with five stops](https://raw.githubusercontent.com/TGergely/ha_dpmk/main/docs/images/example-place-map.png) | ![Map card of a single stop](https://raw.githubusercontent.com/TGergely/ha_dpmk/main/docs/images/example-stop-map.png) |

| Place: departures of all its stops | Single stop: departures |
|---|---|
| ![Departures card of a place](https://raw.githubusercontent.com/TGergely/ha_dpmk/main/docs/images/example-place-departures.png) | ![Departures card of a single stop](https://raw.githubusercontent.com/TGergely/ha_dpmk/main/docs/images/example-stop-departures.png) |

## Install with HACS (custom repository)

1. In Home Assistant open **HACS**, then the ⋮ menu (top right), then **Custom repositories**.
2. Enter this repository's URL, choose the type **Integration**, and click **Add**.
3. Search for **Košice Public Transport – DPMK** (or just `DPMK`) in HACS, click **Download**, and **restart Home Assistant**.
4. Go to **Settings → Devices & services → Add integration → Košice Public Transport – DPMK**.

### Manual install

Copy the folder `custom_components/dpmk` into your Home Assistant `config/custom_components/` folder (so that `config/custom_components/dpmk/manifest.json` exists) and restart Home Assistant.

Needs Home Assistant 2024.7 or newer.

## Set up

Go to **Settings → Devices & services → Add integration → Košice Public Transport – DPMK** and choose:

- **One stop, chosen from the list.** The list is built into the integration: all 262 DPMK stops, each with its district (for example `Hlavná pošta - Staré mesto`). When your Home Assistant is in Košice, the nearest stops come first with their distance. Two stops share the name `Ludvíkov Dvor - Šaca`, so those two also show their stop number. If a stop is missing from the list (DPMK added one after the list was made), type its number in the second field; it is the number in `dpmk.sk/cp/zastavka/<number>`.
- **A place with several nearby stops** (below).

Repeat for as many stops or places as you like. A stop that is already added is refused.

The map centres itself on the stop. Every stop has a position: 248 come from the city's open data, and the 14 stops that it lacks (for example `Panoráma - Vyšné Opátske`) come from OpenStreetMap. If a position is off, set the map centre yourself in **Configure**.

## Places: several stops near you

If two to five stops are close to where you live, add them as one **place**:

1. Choose **A place with several nearby stops**, name it (for example `Home`), and put it on the map with a radius (300 m is a good start).
2. The integration lists the DPMK stops around the spot with their distances. The ones **inside your radius are ticked** (at most the 8 nearest); the next ones just outside it (up to about 800 m, or twice the radius) are offered unticked, so a stop that is a little too far is one tick away.
3. You get **one sensor** and **one device**. The departures of all the stops are merged into one list sorted by time, and each row says which stop it is from. The map shows every stop as a named dot, and each vehicle's minutes are to the stop it is heading for.

You can change the stops, the map centre and the radius later in **Configure**.

## Default stop

In **Configure**, turn on **Use as the default for cards** for one stop or place. A card without an `entity` then shows it (if none is marked, the first DPMK sensor is used). This lets you add a card without choosing a sensor.

## Cards

The cards are registered automatically. Add them from the card picker (**DPMK odchody**, **DPMK mapa**) or in YAML. `entity` is the sensor of your stop or place; leave it out to use the default stop.

### Departures

```yaml
type: custom:dpmk-departures-card
entity: sensor.dpmk_hlavna_posta_stare_mesto_next_departure
title: Hlavná pošta   # optional, defaults to the stop name
max_rows: 6           # optional, 1-20
show_delay: true      # optional
language: sk          # optional: sk | en | auto. Leave it out to use the integration setting
```

```
[35]  Exnárova                      ● 09:54 [09:55]
      o 6 min · +1 min
```

The main time is the official timetable time. The bracket is the real time (timetable plus the live delay) and appears only for trips that have live data (green dot). Rows without a dot are timetable only, because that vehicle has not started its trip yet.

### Map

```yaml
type: custom:dpmk-map-card
entity: sensor.dpmk_hlavna_posta_stare_mesto_next_departure
title: Vozidlá pri zastávke   # optional
show_legend: true             # optional
background: map               # map (default) | none  (none = plain radar view)
map_style: auto               # auto (follows the theme) | light | dark
show_rings: false             # draw distance rings over the map
language: sk                  # optional: sk | en | auto. Leave it out to use the integration setting
```

- The picture covers the radius you set in the integration options.
- Vehicle labels show the live minutes to your stop. A vehicle with no matching departure (for example one that already passed) shows its distance instead.
- Movement (green/red ring) is worked out from two readings, so a new vehicle starts white for one refresh.

## Options

Open **Settings → Devices & services → Košice Public Transport – DPMK → Configure**.

| Option | Meaning | Default |
|---|---|---|
| Lines/directions | Limit the stop to the lines and directions you care about (empty = all) | all |
| Language of the cards | Slovak, English, or automatic (follow the Home Assistant language). A card's own `language` option overrides it | Automatic |
| Update interval | How often the live feed is read, **5 to 120 s** | 10 s |
| Vehicles shown on the map | Only vehicles serving this stop (line **and** direction), or all vehicles in range (others dimmed, no ring or label) | serving |
| Stops of this place | (places only) which stops belong to the place: the ones within 1 km, plus those you chose | the ones you ticked |
| Put the map where the stop is | (single stops) centre the map on the stop's own position; turn off to use a point of your own | on |
| Map centre | The centre of the map for a place, or for a stop when the option above is off | the stop or place |
| Map radius | How far around the centre vehicles are shown, 200 to 5000 m | 1500 m |
| Use as the default for cards | Cards without an `entity` use this stop or place | off |
| Number of departures | Rows kept in the sensor attribute, 1 to 20 | 8 |
| Timetable variant on weekdays | DPMK has school-year and school-holiday timetables. `auto` treats July, August and 23 Dec to 6 Jan as holidays. Use `school` or `holidays` for other breaks (autumn, winter, spring) | auto |

Weekends and Slovak public holidays always use the "free days" timetable.

## How it works

- **The stop list** is a file inside the integration (`data/stops.json`), so adding a stop makes no request. It joins the stop list of dpmk.sk with the stop positions of the city's open data, and OpenStreetMap for the few stops that data lacks. `tools/build_stops.py` rebuilds it; run it before a release, because DPMK may add or rename stops.
- **Timetables** come from the current timetable pages of dpmk.sk (cached for 12 hours). On start-up the integration fetches a few extra pages per line, so it can tell where each trip starts. Trips that start partway along a line are handled as well. A place with 7 stops needs about 350 pages for this, fetched three at a time (a few seconds) once at start-up and then every 12 hours; a normal refresh makes no timetable request.
- **Live data** comes from the feed behind DPMK's own map page, `https://www.dpmk.sk/api/cp/map` (position, delay, direction and start time of every running vehicle). A vehicle is matched to a timetable trip by its line, direction and start time, so the delay is applied to the right departure. The real time assumes the vehicle's current delay stays the same until your stop.
- **Request rate**: all stops share one cached read of the live feed. It is never requested more often than every **5 seconds**, whatever you configure. Timetables are requested only at start-up and then every 12 hours.
- **Line colors** are read from DPMK's stylesheet, so they follow DPMK's own palette. Lines that DPMK leaves uncolored are shown gray.
- **Map tiles** are Esri's gray base maps (© Esri, HERE, Garmin, © OpenStreetMap contributors). They need no key. Your browser loads them directly, so Esri can see the map area and your IP address, like with any web map. Use `background: none` to avoid that.

## Good to know

- DPMK refreshes a vehicle's position only about every **20 seconds** (sometimes up to a minute), and vehicles occasionally drop out of the feed for a while when their GPS signal is lost. A bus that is close to your stop can therefore appear late. Update intervals below 10 s rarely help.
- The feed has no destination or heading. Arriving or leaving is guessed from whether a vehicle gets closer to or farther from your stop between readings, using straight-line distance.
- Only DPMK Košice city lines are covered.

## Troubleshooting

**"Custom element doesn't exist: dpmk-departures-card" (or the map card)**
1. Open `http://YOUR_HA:8123/dpmk_static/dpmk-departures-card.js`. You should see JavaScript code. If not, the integration is not loaded: check **Settings → System → Logs** for `dpmk`.
2. Clear the frontend cache (Ctrl+F5, or in the phone app: Settings → Companion App → Debugging → Reset frontend cache).
3. If it still fails, add the file as a dashboard resource: **Settings → Dashboards → ⋮ → Resources → Add resource**, URL `/dpmk_static/dpmk-departures-card.js?v=1` (change the number after an update), type **JavaScript module**. The file protects itself against being loaded twice.

**Only a few buses on the map** — the radius is probably small. Increase it in the options (1500 m is a good start). Buses without a green dot in the departures list have not started their trip yet and are not on the map.

**Buses missing for a minute or two even though they are near** — see "Good to know". It is usually the DPMK feed, not the integration.

**My stop is not in the list** — use the stop number field when adding (the number in `dpmk.sk/cp/zastavka/<number>`), and please open an issue so the list can be updated.

**The map is in the wrong place for a stop** — in **Configure** turn off "Put the map where the stop is" and choose the centre yourself.

**Wrong timetable on a weekday during a school break** — set "Timetable variant on weekdays" to `holidays`.

**Debug log**: add this to `configuration.yaml` and restart.

```yaml
logger:
  logs:
    custom_components.dpmk: debug
```

## Repository layout

```
custom_components/dpmk/
  api.py            dpmk.sk client and page parsers
  schedule.py       departures, live matching, nearby vehicles, movement
  coordinator.py    caching, shared live feed, update loop (one stop or a place)
  stops.py          the built-in stop list and "stops near a point"
  data/stops.json   the stop list: id, name, district, position, poles
  sensor.py         next-departure sensor
  config_flow.py    add a stop or a place, options
  www/dpmk-departures-card.js   both Lovelace cards
  translations/     en, sk
tools/build_stops.py   rebuilds data/stops.json (needs the internet)
docs/images/           the example pictures above
hacs.json
```

## Sensor names

Each stop or place has one device called `DPMK <name>` with one sensor, for example `sensor.dpmk_heringes_vysne_opatske_next_departure` (a stop) or `sensor.dpmk_home_next_departure` (a place called "Home"). Sensors created by version 0.2.0 or older keep their old ids, which Home Assistant never renames by itself; you can rename them in the sensor's settings (**Entity ID**).

## Versions

See [CHANGELOG.md](https://github.com/TGergely/ha_dpmk/blob/main/CHANGELOG.md). The version is set in `custom_components/dpmk/manifest.json`. HACS offers an update when a new GitHub release is published.

The integration icon and logo are in `custom_components/dpmk/brand/`. Home Assistant 2026.3 and newer show them directly. On older versions, or in the HACS list, the generic icon may appear until the images are also added to the [home-assistant/brands](https://github.com/home-assistant/brands) repository.

## Contributing and license

Contributions are welcome: open an issue, or fork the repository and send a pull request.

Released under the [MIT License](https://github.com/TGergely/ha_dpmk/blob/main/LICENSE). The DPMK timetable and live data, and the Esri / OpenStreetMap map tiles, are not covered by it and stay under their owners' terms (see "Credits and data").

## Credits and data

Timetables and live positions: DPMK, a.s. (dpmk.sk). Stop positions: "Zastávky MHD", open data of the City of Košice, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) ([dataset](https://opendata.kosice.sk/datasets/027eaebb18144e8c9eecbf04a8ff4093)); the integration's `data/stops.json` contains a processed copy. The positions of 14 stops (marked `position_source: osm` in that file) and the map are from © OpenStreetMap contributors (ODbL), and the map tiles are by Esri, HERE, Garmin. This project is not endorsed by any of them.

## Stručne po slovensky

Integrácia pre Home Assistant, ktorá ukazuje odchody liniek MHD DPMK Košice zo zvolenej zastávky s aktuálnym meškaním a jednoduchú mapu vozidiel v okolí zastávky. Inštalácia cez HACS: ⋮ → *Custom repositories* → adresa repozitára → typ *Integration* → stiahnuť → reštart → *Pridať integráciu* → Košice Public Transport – DPMK. Zastávku vyberiete zo zoznamu všetkých zastávok DPMK, ktorý je súčasťou integrácie. Môžete pridať aj *miesto* s viacerými zastávkami v okolí (napríklad doma): jeden senzor, jeden zoznam odchodov a jedna mapa. Mapa sa vycentruje na zastávku sama; stred a okruh sa dajú zmeniť v *Konfigurovať*, kde sa dá nastaviť aj predvolená zastávka pre karty bez zvolenej entity. Karty `DPMK odchody` a `DPMK mapa` sú v zozname kariet a sú predvolene v jazyku podľa Home Assistanta (slovensky alebo anglicky), jazyk sa dá zmeniť v *Konfigurovať*. Neoficiálne, bez väzby na DPMK, a.s.

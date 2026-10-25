"""Data coordinator: cached timetables + live vehicle feed -> departures for a stop or a place."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DpmkApi, Route, Timetable
from .const import (
    CONF_AUTO_LOCATION,
    CONF_IS_DEFAULT,
    CONF_LANGUAGE,
    CONF_LOCATION,
    CONF_MAP_RADIUS,
    CONF_MAP_SCOPE,
    CONF_MAX_DEPARTURES,
    CONF_PLACE_LOCATION,
    CONF_PLACE_NAME,
    CONF_ROUTES,
    CONF_SCHOOL_MODE,
    CONF_STOP_ID,
    CONF_STOP_IDS,
    CONF_STOP_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_DEPARTURES,
    DEFAULT_RADIUS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    SCHEDULE_TTL_SECONDS,
    SCHOOL_AUTO,
    SCOPE_ALL,
    SCOPE_SERVING,
)
from .schedule import build_departures, classify_movement, distance_m, nearby_vehicles, offset_m
from .stops import Catalog

_LOGGER = logging.getLogger(__name__)

MAX_START_LOOKUPS = 12  # extra timetable pages fetched per line direction to find trip starts


def clamp_interval(value) -> int:
    """Refresh interval in seconds, kept within the allowed range."""
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        seconds = DEFAULT_UPDATE_INTERVAL
    return max(MIN_UPDATE_INTERVAL, min(MAX_UPDATE_INTERVAL, seconds))


class LiveFeed:
    """One shared cache of the live vehicle feed for all entries.

    However many stops are configured, and whatever interval they ask for, the feed is
    requested at most once per MIN_UPDATE_INTERVAL seconds.
    """

    def __init__(self, api: DpmkApi) -> None:
        self._api = api
        self._lock = asyncio.Lock()
        self._at: float | None = None
        self._data: list[dict] = []

    async def get(self, max_age: float) -> list[dict]:
        """Return the feed, fetching again only if the cached copy is older than max_age."""
        async with self._lock:
            age = None if self._at is None else time.monotonic() - self._at
            if age is None or age >= max(MIN_UPDATE_INTERVAL, max_age):
                self._data = await self._api.get_vehicles()
                self._at = time.monotonic()
            return self._data


class DpmkCoordinator(DataUpdateCoordinator[dict]):
    """One config entry: a single stop, or a place made of several stops."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, live: LiveFeed, catalog: Catalog
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(
                seconds=clamp_interval(entry.options.get(CONF_UPDATE_INTERVAL))
            ),
        )
        self.entry = entry
        self.api = DpmkApi(async_get_clientsession(hass))
        self.live = live
        self.catalog = catalog
        # per stop id: every route (unfiltered, for the options form) and the loaded timetables
        self.routes_by_stop: dict[str, list[Route]] = {}
        self._schedule: dict[str, list[tuple[Route, Timetable, Timetable | None]]] = {}
        self._names: dict[str, str] = {}
        self._pages: dict[tuple, Timetable] = {}
        self._schedule_at = 0.0
        self._colors: dict[str, dict[str, str]] = {}
        self._types: dict[str, str] = {}
        self._distances: dict[str, float] = {}

    # ---- what this entry is made of -------------------------------------------------------

    @property
    def is_place(self) -> bool:
        return CONF_STOP_IDS in self.entry.data

    @property
    def stop_ids(self) -> list[str]:
        ids = self.entry.options.get(CONF_STOP_IDS) or self.entry.data.get(CONF_STOP_IDS)
        if ids:
            return [str(i) for i in ids]
        return [str(self.entry.data[CONF_STOP_ID])]

    @property
    def display_name(self) -> str:
        data = self.entry.data
        return data.get(CONF_PLACE_NAME) or data.get(CONF_STOP_NAME) or self.entry.title

    @property
    def center(self) -> tuple[float, float]:
        """Where the map is centred: a stop's own position, a place's spot, or a chosen point."""
        opts = self.entry.options
        loc = opts.get(CONF_LOCATION) or {}
        chosen = (loc["latitude"], loc["longitude"]) if "latitude" in loc and "longitude" in loc else None
        if self.is_place:
            base = self.entry.data.get(CONF_PLACE_LOCATION) or {}
            if chosen:
                return chosen
            if "latitude" in base:
                return base["latitude"], base["longitude"]
        else:
            info = self.catalog.get(self.stop_ids[0])
            if opts.get(CONF_AUTO_LOCATION, chosen is None) and info and info.has_position:
                return info.lat, info.lng
            if chosen:
                return chosen
        return self.hass.config.latitude, self.hass.config.longitude

    @property
    def map_radius(self) -> float:
        loc = self.entry.options.get(CONF_LOCATION) or {}
        return float(self.entry.options.get(CONF_MAP_RADIUS) or loc.get("radius") or DEFAULT_RADIUS)

    @property
    def location(self) -> tuple[float, float, float]:
        """(latitude, longitude, map radius in metres)."""
        lat, lng = self.center
        return lat, lng, self.map_radius

    @property
    def all_routes(self) -> list[tuple[str, Route]]:
        return [(sid, r) for sid, routes in self.routes_by_stop.items() for r in routes]

    # ---- loading the timetables ------------------------------------------------------------

    async def _page(self, route: Route, stop_id: str, seq: str | None = None) -> Timetable:
        """A timetable page, fetched once per load (stops of a place share many of them)."""
        key = (route.line_id, route.direction, stop_id, seq or route.seq)
        if key not in self._pages:
            self._pages[key] = await self.api.get_timetable(route, stop_id, seq)
        return self._pages[key]

    async def _trip_starts(self, stop_id: str, route: Route, table: Timetable) -> Timetable:
        """Start time of every trip serving this stop, as a pseudo timetable (conn id -> minutes).

        The live feed identifies a trip by the time it left its first stop. Not every trip starts
        at the line's first stop, so walk the stops in travel order until each trip has been seen
        at its first stop (the first stop where it appears is its start). Capped to stay polite.
        """
        starts: dict[str, dict[str, int]] = {dtype: {} for dtype in table.tables}
        ids = [s for s, _ in table.stops]
        end = ids.index(stop_id) + 1 if stop_id in ids else len(ids)
        for fetched, (page_stop, seq) in enumerate(table.stops[:end]):
            if all(c in starts[d] for d, rows in table.tables.items() for c, _ in rows):
                break
            if fetched >= MAX_START_LOOKUPS:
                break
            page = table if page_stop == stop_id else await self._page(route, page_stop, seq)
            for dtype, rows in page.tables.items():
                if dtype in starts:
                    for conn, minutes in rows:
                        starts[dtype].setdefault(conn, minutes)
        return Timetable(stops=[], tables={d: list(s.items()) for d, s in starts.items()})

    async def _load_schedule(self) -> None:
        self._pages = {}
        wanted = self.entry.options.get(CONF_ROUTES)
        sem = asyncio.Semaphore(3)
        schedule: dict[str, list] = {}
        routes_by_stop: dict[str, list[Route]] = {}
        names: dict[str, str] = {}
        errors: list[Exception] = []

        async def load_route(stop_id: str, route: Route):
            async with sem:
                table = await self._page(route, stop_id)
                return route, table, await self._trip_starts(stop_id, route, table)

        for stop_id in self.stop_ids:
            try:
                stop = await self.api.get_stop(stop_id)
                routes_by_stop[stop_id] = stop.routes
                info = self.catalog.get(stop_id)
                names[stop_id] = info.name if info else stop.name
                chosen = [r for r in stop.routes if not wanted or r.key in wanted]
                schedule[stop_id] = list(await asyncio.gather(*(load_route(stop_id, r) for r in chosen)))
            except Exception as err:  # one stop of a place failing must not hide the others
                _LOGGER.warning("Could not load stop %s: %s", stop_id, err)
                errors.append(err)
        if not schedule:
            raise errors[0] if errors else UpdateFailed("no stops configured")
        try:
            self._colors = await self.api.get_line_colors()
            if self.entry.options.get(CONF_MAP_SCOPE) == SCOPE_ALL:
                self._types = await self.api.get_line_types()  # bus/tram shape of unrelated lines
        except Exception as err:  # cosmetic only: the card falls back to default colours
            _LOGGER.debug("Could not load line colours: %s", err)
        self._schedule, self.routes_by_stop, self._names = schedule, routes_by_stop, names
        self._schedule_at = time.monotonic()

    # ---- the refresh -----------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        try:
            if not self._schedule or time.monotonic() - self._schedule_at > SCHEDULE_TTL_SECONDS:
                await self._load_schedule()
            try:
                # a hair under our own interval, so every refresh gets fresh data, never <5 s
                vehicles = await self.live.get(self.update_interval.total_seconds() - 0.5)
            except Exception as err:  # live data is optional: fall back to timetable
                _LOGGER.debug("Live feed unavailable: %s", err)
                vehicles = []
        except Exception as err:
            raise UpdateFailed(f"DPMK request failed: {err}") from err

        now = dt_util.now()
        opts = self.entry.options
        school = opts.get(CONF_SCHOOL_MODE, SCHOOL_AUTO)
        multi = len(self._schedule) > 1

        # Long lists per stop: the map needs the live ETA of buses beyond the displayed rows.
        everything = []
        for stop_id, routes in self._schedule.items():
            everything += build_departures(
                routes, vehicles, now, school, limit=80,
                stop_name=self._names.get(stop_id), stop_id=stop_id,
            )
        everything.sort(key=lambda d: d.expected)
        departures = everything[: int(opts.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES))]

        # for every running vehicle: when it reaches the first of our stops it is heading to
        eta: dict[str, str] = {}
        eta_stop: dict[str, str] = {}
        for d in everything:
            if d.vehicle_id and d.vehicle_id not in eta:
                eta[d.vehicle_id] = d.expected.isoformat()
                eta_stop[d.vehicle_id] = d.stop_id

        clat, clng, radius = self.location
        all_routes = [r for routes in self._schedule.values() for r, _, _ in routes]
        lines = {r.line for r in all_routes}
        served = {(r.line, r.direction) for r in all_routes}
        only_served = opts.get(CONF_MAP_SCOPE, SCOPE_SERVING) != SCOPE_ALL
        near = nearby_vehicles(vehicles, served, clat, clng, radius, only_served)
        types = self._types | {r.line: r.line_type for _, r in self.all_routes}

        points: dict[str, tuple[float, float]] = {}
        for stop_id in self._schedule:
            info = self.catalog.get(stop_id)
            if info and info.has_position:
                points[stop_id] = (info.lat, info.lng)

        distances: dict[str, float] = {}
        for v in near:
            target_id = eta_stop.get(v["id"])
            tlat, tlng = points.get(target_id) or (clat, clng)
            # distance and movement are measured to the stop the vehicle is heading for
            v["distance"] = round(distance_m(tlat, tlng, v["latitude"], v["longitude"]))
            v["movement"] = classify_movement(self._distances.get(v["id"]), v["distance"])
            distances[v["id"]] = v["distance"]
            v["stop"] = self._names.get(target_id) if multi and target_id else None
            v["type"] = types.get(v["line"])
            v["bg"] = self._colors.get(v["line"], {}).get("bg")
            v["fg"] = self._colors.get(v["line"], {}).get("fg")
            v["eta"] = eta.get(v["id"])
        self._distances = distances

        rows = []
        for d in departures:
            row = d.as_dict(now)
            row["bg"] = self._colors.get(d.line, {}).get("bg")
            row["fg"] = self._colors.get(d.line, {}).get("fg")
            rows.append(row)

        stops = []
        for stop_id, (slat, slng) in points.items():
            dx, dy = offset_m(clat, clng, slat, slng)
            stops.append({"id": stop_id, "name": self._names.get(stop_id), "dx": dx, "dy": dy})

        return {
            "departures": rows,
            "lines": sorted(lines),
            "vehicles": near,
            "stops": stops,
            "multi_stop": multi,
            "name": self.display_name,
            "is_default": bool(opts.get(CONF_IS_DEFAULT)),
            "radius": radius,
            "language": opts.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            "live_vehicles": len(vehicles),
        }

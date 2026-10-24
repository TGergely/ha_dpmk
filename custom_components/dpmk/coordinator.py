"""Data coordinator: cached timetables + live vehicle feed -> departures."""

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

from .api import DpmkApi, Route, Stop, Timetable
from .const import (
    CONF_LOCATION,
    CONF_MAP_SCOPE,
    CONF_MAX_DEPARTURES,
    CONF_ROUTES,
    CONF_SCHOOL_MODE,
    CONF_STOP_ID,
    DEFAULT_MAX_DEPARTURES,
    DEFAULT_RADIUS,
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    SCHEDULE_TTL_SECONDS,
    SCHOOL_AUTO,
    SCOPE_ALL,
    SCOPE_SERVING,
)
from .schedule import build_departures, classify_movement, nearby_vehicles

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
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, live: LiveFeed) -> None:
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
        self.stop: Stop | None = None
        self._schedule: list[tuple[Route, Timetable, Timetable | None]] = []
        self._schedule_at = 0.0
        self._colors: dict[str, dict[str, str]] = {}
        self._types: dict[str, str] = {}
        self._distances: dict[str, float] = {}

    @property
    def location(self) -> tuple[float, float, float]:
        """Stop position and map radius; defaults to the Home Assistant home."""
        loc = self.entry.options.get(CONF_LOCATION) or {}
        return (
            loc.get("latitude", self.hass.config.latitude),
            loc.get("longitude", self.hass.config.longitude),
            loc.get("radius", DEFAULT_RADIUS),
        )

    @property
    def stop_id(self) -> str:
        return self.entry.data[CONF_STOP_ID]

    async def _trip_starts(self, route: Route, table: Timetable) -> Timetable:
        """Start time of every trip serving this stop, as a pseudo timetable (conn id -> minutes).

        The live feed identifies a trip by the time it left its first stop. Not every trip starts
        at the line's first stop, so walk the stops in travel order until each trip has been seen
        at its first stop (the first stop where it appears is its start). Capped to stay polite.
        """
        starts: dict[str, dict[str, int]] = {dtype: {} for dtype in table.tables}
        ids = [s for s, _ in table.stops]
        end = ids.index(self.stop_id) + 1 if self.stop_id in ids else len(ids)
        for fetched, (stop_id, seq) in enumerate(table.stops[:end]):
            if all(c in starts[d] for d, rows in table.tables.items() for c, _ in rows):
                break
            if fetched >= MAX_START_LOOKUPS:
                break
            page = table if stop_id == self.stop_id else await self.api.get_timetable(route, stop_id, seq)
            for dtype, rows in page.tables.items():
                if dtype in starts:
                    for conn, minutes in rows:
                        starts[dtype].setdefault(conn, minutes)
        return Timetable(stops=[], tables={d: list(s.items()) for d, s in starts.items()})

    async def _load_schedule(self) -> None:
        stop = await self.api.get_stop(self.stop_id)
        wanted = self.entry.options.get(CONF_ROUTES)
        routes = [r for r in stop.routes if not wanted or r.key in wanted]
        sem = asyncio.Semaphore(3)

        async def load(route: Route):
            async with sem:
                table = await self.api.get_timetable(route, self.stop_id)
                return route, table, await self._trip_starts(route, table)

        self._schedule = list(await asyncio.gather(*(load(r) for r in routes)))
        try:
            self._colors = await self.api.get_line_colors()
            if self.entry.options.get(CONF_MAP_SCOPE) == SCOPE_ALL:
                self._types = await self.api.get_line_types()  # bus/tram shape of unrelated lines
        except Exception as err:  # cosmetic only: the card falls back to default colours
            _LOGGER.debug("Could not load line colours: %s", err)
        self.stop = stop
        self._schedule_at = time.monotonic()

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
        # Build a long list: the map needs the live ETA of buses beyond the displayed rows.
        everything = build_departures(
            self._schedule, vehicles, now, opts.get(CONF_SCHOOL_MODE, SCHOOL_AUTO), limit=80
        )
        departures = everything[: int(opts.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES))]
        eta: dict[str, str] = {}
        for d in everything:
            if d.vehicle_id and d.vehicle_id not in eta:
                eta[d.vehicle_id] = d.expected.isoformat()
        lat, lng, radius = self.location
        lines = {r.line for r, _, _ in self._schedule}
        served = {(r.line, r.direction) for r, _, _ in self._schedule}
        only_served = opts.get(CONF_MAP_SCOPE, SCOPE_SERVING) != SCOPE_ALL
        near = nearby_vehicles(vehicles, served, lat, lng, radius, only_served)
        types = self._types | {r.line: r.line_type for r, _, _ in self._schedule}
        distances = {}
        for v in near:
            v["movement"] = classify_movement(self._distances.get(v["id"]), v["distance"])
            distances[v["id"]] = v["distance"]
        self._distances = distances
        for v in near:
            v["type"] = types.get(v["line"])
            v["bg"] = self._colors.get(v["line"], {}).get("bg")
            v["fg"] = self._colors.get(v["line"], {}).get("fg")
            v["eta"] = eta.get(v["id"])
        rows = []
        for d in departures:
            row = d.as_dict(now)
            row["bg"] = self._colors.get(d.line, {}).get("bg")
            row["fg"] = self._colors.get(d.line, {}).get("fg")
            rows.append(row)
        return {
            "departures": rows,
            "lines": sorted(lines),
            "vehicles": near,
            "radius": radius,
            "live_vehicles": len(vehicles),
        }

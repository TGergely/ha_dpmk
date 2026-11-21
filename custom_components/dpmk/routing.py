"""Route planning for the cards: loads and keeps the network, asks the planner, adds live delays."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import DpmkApi, Pattern, Route
from .const import CONF_SCHOOL_MODE, DOMAIN, SCHEDULE_TTL_SECONDS, SCHOOL_AUTO
from .planner import WALK_METERS_PER_MINUTE, Connection, Network, Tables, plan_route
from .schedule import day_type_for, index_vehicles
from .stops import Catalog, sort_key

_LOGGER = logging.getLogger(__name__)

NETWORK_VERSION = 1
WALK_RADIUS_M = 250  # stops this close count as one place for a change
SEARCH_BACK = timedelta(hours=3)  # "arrive by" looks for departures this long before the wanted time
MAX_ROWS = 8


class RoutingError(Exception):
    """A search that cannot be answered; the code is turned into a message on the card."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Router:
    """One per Home Assistant: the network, a cache of timetable pages, and the search itself."""

    def __init__(self, hass: HomeAssistant, live, catalog: Catalog) -> None:
        self.hass = hass
        self.live = live
        self.catalog = catalog
        self.api = DpmkApi(async_get_clientsession(hass))
        self._store = Store(hass, NETWORK_VERSION, f"{DOMAIN}.network")
        self._network: Network | None = None
        self._network_until = 0.0  # monotonic time after which the network is loaded again
        self._lock = asyncio.Lock()
        self._tables: dict[tuple[str, str, str], tuple[float, Tables]] = {}
        self._colors: dict[str, dict[str, str]] = {}
        self._colors_until = 0.0
        self._walk: dict[str, list[tuple[str, int]]] = {}

    # ---- the network -----------------------------------------------------------------------

    async def network(self) -> Network:
        async with self._lock:
            if self._network is not None and time.monotonic() < self._network_until:
                return self._network
            if self._network is None:
                await self._restore()
            if self._network is None or time.monotonic() >= self._network_until:
                try:
                    await self._download()
                except Exception as err:
                    if self._network is None:
                        raise RoutingError("unavailable") from err
                    _LOGGER.warning("Could not refresh the line network, using the saved one: %s", err)
                    self._network_until = time.monotonic() + 600
            return self._network

    async def _restore(self) -> None:
        try:
            data = await self._store.async_load()
            if not data:
                return
            patterns = [Pattern.from_json(p) for p in data["patterns"]]
            age = time.time() - float(data["saved"])
        except Exception as err:  # unreadable: download afresh
            _LOGGER.debug("Ignoring the saved line network: %s", err)
            return
        if patterns:
            self._network = Network(patterns)
            self._network_until = time.monotonic() + max(0.0, SCHEDULE_TTL_SECONDS - age)

    async def _download(self) -> None:
        ids = await self.api.get_line_ids()
        sem = asyncio.Semaphore(3)

        async def one(line_id: str) -> list[Pattern]:
            async with sem:
                return await self.api.get_patterns(line_id)

        patterns = [p for group in await asyncio.gather(*(one(i) for i in ids)) for p in group]
        if not patterns:
            raise RoutingError("unavailable")
        self._network = Network(patterns)
        self._network_until = time.monotonic() + SCHEDULE_TTL_SECONDS
        self._tables.clear()  # a new timetable version: the pages are renewed too
        try:
            await self._store.async_save({"saved": time.time(), "patterns": [p.to_json() for p in patterns]})
        except Exception as err:  # only a slower next start
            _LOGGER.debug("Could not save the line network: %s", err)

    # ---- timetables ------------------------------------------------------------------------

    async def table(self, pattern: Pattern, stop_id: str) -> Tables:
        key = (pattern.line_id, pattern.direction, stop_id)
        hit = self._tables.get(key)
        if hit and time.monotonic() < hit[0]:
            return hit[1]
        seq = dict(pattern.stops).get(stop_id)
        route = Route(pattern.line_id, pattern.line, pattern.line_type, pattern.destination, seq or "", pattern.direction)
        page = await self.api.get_timetable(route, stop_id, seq)
        tables = {dtype: dict(rows) for dtype, rows in page.tables.items()}
        self._tables[key] = (time.monotonic() + SCHEDULE_TTL_SECONDS, tables)
        return tables

    async def _line_colors(self) -> dict[str, dict[str, str]]:
        if time.monotonic() >= self._colors_until:
            try:
                self._colors = await self.api.get_line_colors()
                self._colors_until = time.monotonic() + SCHEDULE_TTL_SECONDS
            except Exception as err:  # cosmetic only
                _LOGGER.debug("Could not load line colours: %s", err)
                self._colors_until = time.monotonic() + 600
        return self._colors

    # ---- helpers ---------------------------------------------------------------------------

    def _school_mode(self) -> str:
        entries = self.hass.config_entries.async_entries(DOMAIN)
        return entries[0].options.get(CONF_SCHOOL_MODE, SCHOOL_AUTO) if entries else SCHOOL_AUTO

    def _neighbours(self, stop_id: str) -> list[tuple[str, int]]:
        """Other stops within walking distance, with the minutes it takes."""
        if stop_id not in self._walk:
            info = self.catalog.get(stop_id)
            found: list[tuple[str, int]] = []
            if info and info.has_position:
                for other, dist in self.catalog.near(info.lat, info.lng, WALK_RADIUS_M):
                    if other.stop_id != stop_id:
                        found.append((other.stop_id, max(1, round(dist / WALK_METERS_PER_MINUTE))))
            self._walk[stop_id] = found
        return self._walk[stop_id]

    def stop_name(self, stop_id: str) -> str:
        info = self.catalog.get(stop_id)
        return info.name if info else stop_id

    def stop_list(self) -> list[dict]:
        """Every stop for the pick lists on the cards, A to Z."""
        items = sorted(self.catalog.stops.values(), key=lambda s: sort_key(s.label))
        return [{"id": s.stop_id, "name": s.name, "label": s.label} for s in items]

    # ---- the search ------------------------------------------------------------------------

    async def plan(self, start: str, end: str, mode: str = "now", at: str | None = None, limit: int = 4) -> dict:
        if start == end:
            raise RoutingError("same_stop")
        if self.catalog.get(start) is None or self.catalog.get(end) is None:
            raise RoutingError("unknown_stop")
        limit = max(1, min(MAX_ROWS, int(limit)))
        network = await self.network()
        if start not in network.at or end not in network.at:
            raise RoutingError("no_service")
        now = dt_util.now()
        school = self._school_mode()

        target = self._resolve_time(mode, at, now)
        search_from = target - SEARCH_BACK if mode == "arrive" else target
        try:
            found = await plan_route(
                network, self.table, [start], [end], search_from, school,
                limit=40 if mode == "arrive" else limit, neighbours=self._neighbours,
            )
        except RoutingError:
            raise
        except Exception as err:
            _LOGGER.debug("Route search failed: %s", err)
            raise RoutingError("unavailable") from err
        if mode == "arrive":
            found = [c for c in found if c.arrive <= target][-limit:]

        delays = await self._live_delays(found, school, now)
        colors = await self._line_colors()
        return {
            "from": self.stop_name(start),
            "to": self.stop_name(end),
            "mode": mode,
            "searched": target.isoformat(),
            "connections": [self._describe(c, delays, colors) for c in found],
        }

    @staticmethod
    def _resolve_time(mode: str, at: str | None, now: datetime) -> datetime:
        if mode == "now" or not at:
            return now
        try:
            hour, minute = (int(x) for x in at.split(":")[:2])
            chosen = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError as err:
            raise RoutingError("bad_time") from err
        # a time that has already passed by more than a few minutes means tomorrow
        return chosen + timedelta(days=1) if chosen < now - timedelta(minutes=5) else chosen

    async def _live_delays(self, found: list[Connection], school: str, now: datetime) -> dict[tuple, int]:
        """Delay in seconds of the first vehicle of each connection, where DPMK reports one."""
        wanted = {c.legs[0] for c in found if c.legs[0].day_offset == 0}
        if not wanted:
            return {}
        try:
            vehicles = await self.live.get(10)
        except Exception as err:  # live data is optional
            _LOGGER.debug("Live feed unavailable for the route search: %s", err)
            return {}
        live = index_vehicles(vehicles)
        out: dict[tuple, int] = {}
        dtype = day_type_for(now.date(), school)
        for leg in wanted:
            running = live.get((leg.pattern.line, leg.pattern.direction))
            if not running:
                continue
            try:
                firsts = await self.table(leg.pattern, leg.pattern.stops[0][0])
            except Exception:
                continue
            start = firsts.get(dtype, {}).get(leg.trip)
            vehicle = running.get(start) if start is not None else None
            if vehicle is not None:
                out[(leg.pattern.line_id, leg.pattern.direction, leg.trip)] = int(vehicle["Delay"])
        return out

    def _describe(self, c: Connection, delays: dict[tuple, int], colors: dict[str, dict[str, str]]) -> dict:
        legs = []
        for leg in c.legs:
            delay = delays.get((leg.pattern.line_id, leg.pattern.direction, leg.trip))
            legs.append(
                {
                    "line": leg.pattern.line,
                    "type": leg.pattern.line_type,
                    "bg": colors.get(leg.pattern.line, {}).get("bg"),
                    "fg": colors.get(leg.pattern.line, {}).get("fg"),
                    "destination": leg.pattern.destination,
                    "from": self.stop_name(leg.board),
                    "to": self.stop_name(leg.alight),
                    "depart": leg.depart.isoformat(),
                    "arrive": leg.arrive.isoformat(),
                    "live": delay is not None,
                    "delay_min": None if delay is None else round(delay / 60),
                }
            )
        changes = []
        for i, walk in enumerate(c.walk):
            before, after = c.legs[i], c.legs[i + 1]
            gap = int((after.depart - before.arrive).total_seconds() // 60)
            changes.append(
                {
                    "stop": self.stop_name(before.alight),
                    "to_stop": self.stop_name(after.board),
                    "walk": walk,
                    "wait": max(0, gap - walk),
                }
            )
        return {
            "depart": c.depart.isoformat(),
            "arrive": c.arrive.isoformat(),
            "minutes": int((c.arrive - c.depart).total_seconds() // 60),
            "legs": legs,
            "changes": changes,
        }

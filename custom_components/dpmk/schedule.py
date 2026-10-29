"""Turn timetables + live vehicles into a list of upcoming departures."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cached_property
from math import asin, cos, radians, sin, sqrt

from dateutil.easter import easter

from .api import Route, Timetable
from .const import SCHOOL_AUTO, SCHOOL_HOLIDAYS, SCHOOL_SCHOOL

FIXED_HOLIDAYS = {
    (1, 1), (1, 6), (5, 1), (5, 8), (7, 5), (8, 29), (9, 1), (9, 15),
    (11, 1), (11, 17), (12, 24), (12, 25), (12, 26),
}


def is_public_holiday(d: date) -> bool:
    if (d.month, d.day) in FIXED_HOLIDAYS:
        return True
    e = easter(d.year)
    return d in (e - timedelta(days=2), e + timedelta(days=1))


def day_type_for(d: date, school_mode: str) -> str:
    if d.weekday() >= 5 or is_public_holiday(d):
        return "free"
    if school_mode == SCHOOL_HOLIDAYS:
        return "holidays"
    if school_mode == SCHOOL_SCHOOL:
        return "school"
    # auto: summer and Christmas break only; use manual modes for other breaks
    if d.month in (7, 8) or (d.month == 12 and d.day >= 23) or (d.month == 1 and d.day <= 6):
        return "holidays"
    return "school"


@dataclass
class Departure:
    line: str
    line_type: str
    destination: str
    scheduled: datetime
    delay: int | None  # seconds, None = no live data
    vehicle_id: str | None = None  # live vehicle serving this departure, if matched
    stop: str | None = None  # name of the stop, shown on cards when a place has several
    stop_id: str | None = None

    @cached_property
    def expected(self) -> datetime:
        return self.scheduled + timedelta(seconds=self.delay or 0)

    def as_dict(self, now: datetime) -> dict:
        return {
            "line": self.line,
            "type": self.line_type,
            "destination": self.destination,
            "scheduled": self.scheduled.isoformat(),
            "expected": self.expected.isoformat(),
            "delay_min": None if self.delay is None else round(self.delay / 60),
            "live": self.delay is not None,
            "stop": self.stop,
            "minutes": max(0, int((self.expected - now).total_seconds() // 60)),
        }


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(a))


def offset_m(lat0: float, lng0: float, lat: float, lng: float) -> tuple[int, int]:
    """(east, north) offset in metres of a point from a centre, the same maths as nearby_vehicles."""
    return (
        round((lng - lng0) * 111320 * cos(radians(lat0))),
        round((lat - lat0) * 110540),
    )


def classify_movement(previous: float | None, current: float, threshold: float = 15) -> str:
    """approaching / leaving / stopped, from two distances to the stop (metres)."""
    if previous is None:
        return "unknown"
    if abs(current - previous) < threshold:
        return "stopped"
    return "approaching" if current < previous else "leaving"


def nearby_vehicles(
    vehicles: list[dict],
    served: set[tuple[str, str]],
    lat: float,
    lng: float,
    radius: float,
    only_served: bool = True,
) -> list[dict]:
    """Vehicles within radius metres of the point.

    served: the (line, direction) pairs that stop here. With only_served=False vehicles on
    other routes are kept too, flagged serves=False.
    """
    out = []
    metres_per_deg_lng = 111320 * cos(radians(lat))
    for v in vehicles:
        serves = (str(v["Line"]), str(v["Dir"])) in served
        if only_served and not serves:
            continue
        dist = distance_m(lat, lng, v["Lat"], v["Lng"])
        if dist <= radius:
            out.append(
                {
                    "id": f"{v['Line']}_{v['Trip']}_{v['Dir']}",
                    "serves": serves,
                    "line": str(v["Line"]),
                    "latitude": v["Lat"],
                    "longitude": v["Lng"],
                    "delay": int(v["Delay"]),
                    "distance": round(dist),
                    # offset from the stop in metres: east (dx) and north (dy)
                    "dx": round((v["Lng"] - lng) * metres_per_deg_lng),
                    "dy": round((v["Lat"] - lat) * 110540),
                }
            )
    return sorted(out, key=lambda x: x["distance"])


def index_vehicles(vehicles: list[dict]) -> dict[tuple[str, str], dict[int, dict]]:
    """Running vehicles as {(line, direction): {start minute: vehicle}}."""
    out: dict[tuple[str, str], dict[int, dict]] = {}
    for v in vehicles:
        out.setdefault((str(v["Line"]), str(v["Dir"])), {})[int(v["TripTime"])] = v
    return out


# ---- derived timetable data, built once per timetable and kept on it -------------------------


def _times(table: Timetable, dtype: str) -> tuple[list[int], list[str]]:
    """The minutes and conn ids of one day type, sorted by time."""
    key = ("times", dtype)
    if key not in table._cache:
        rows = sorted((minutes, conn) for conn, minutes in table.tables.get(dtype) or [])
        table._cache[key] = ([m for m, _ in rows], [c for _, c in rows])
    return table._cache[key]


def _lookup(table: Timetable, dtype: str) -> dict[str, int]:
    """conn id -> minute, for one day type (the start minutes, for a line-origin timetable)."""
    key = ("lookup", dtype)
    if key not in table._cache:
        table._cache[key] = dict(table.tables.get(dtype, []))
    return table._cache[key]


def _trips_by_start(origin: Timetable, dtype: str) -> dict[int, list[str]]:
    """start minute -> conn ids that leave the first stop at that minute."""
    key = ("by_start", dtype)
    if key not in origin._cache:
        out: dict[int, list[str]] = {}
        for conn, start in origin.tables.get(dtype, []):
            out.setdefault(start, []).append(conn)
        origin._cache[key] = out
    return origin._cache[key]


def build_departures(
    routes: list[tuple[Route, Timetable, Timetable | None]],
    vehicles: list[dict],
    now: datetime,
    school_mode: str = SCHOOL_AUTO,
    limit: int = 8,
    stop_name: str | None = None,
    stop_id: str | None = None,
    live: dict[tuple[str, str], dict[int, dict]] | None = None,
    extra_live: bool = False,
) -> list[Departure]:
    """routes: (route, timetable at the stop, timetable at the line origin).

    Returns the `limit` soonest departures. The timetables are sorted once, so a call only looks at
    the departures around `now` (a binary search) instead of expanding every trip of every day type.

    live: the vehicles indexed by index_vehicles(); pass it when building several stops from one feed.
    extra_live: also return every departure that a running vehicle is matched to, even beyond
    `limit`. The map needs those to tell each vehicle when it reaches the stop.
    """
    if live is None:
        live = index_vehicles(vehicles)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    earliest, latest = now - timedelta(minutes=1), now + timedelta(hours=26)
    days = []
    for offset in (-1, 0, 1):
        day = midnight + timedelta(days=offset)
        # a wall-clock window in minutes since this day's midnight, widened by 90 minutes because
        # the clock changes make wall-clock and real time differ by an hour; the exact check in
        # add() decides, so the widening only costs a few extra comparisons
        wall_day = day.replace(tzinfo=None)
        lo = (earliest.replace(tzinfo=None) - wall_day).total_seconds() / 60 - 90
        hi = (latest.replace(tzinfo=None) - wall_day).total_seconds() / 60 + 90
        days.append((offset, day, day_type_for(day.date(), school_mode), lo, hi))
    per_route = max(limit * 2, 10)  # one route cannot contribute more than this to the soonest `limit`
    result: list[Departure] = []
    seen: set[tuple[int, str, int]] = set()  # (route index, conn id, day offset) already added

    def add(ri, route, trips, offset, day, minutes, conn, starts) -> bool:
        scheduled = day + timedelta(minutes=minutes)
        if not earliest <= scheduled <= latest:
            return False
        delay = None
        vehicle_id = None
        if offset == 0 or minutes >= 1440:
            start = starts.get(conn)
            vehicle = trips.get(start) if start is not None else None
            if vehicle is not None:
                delay = int(vehicle["Delay"])
                vehicle_id = f"{vehicle['Line']}_{vehicle['Trip']}_{vehicle['Dir']}"
        result.append(
            Departure(
                route.line, route.line_type, route.destination, scheduled, delay, vehicle_id,
                stop_name, stop_id,
            )
        )
        seen.add((ri, conn, offset))
        return True

    for ri, (route, table, origin) in enumerate(routes):
        trips = live.get((route.line, route.direction), {})
        taken = 0
        for offset, day, dtype, lo, hi in days:
            minutes_list, conns = _times(table, dtype)
            if not minutes_list:
                continue
            starts = _lookup(origin, dtype) if origin else {}
            for i in range(bisect_left(minutes_list, lo), bisect_right(minutes_list, hi)):
                if add(ri, route, trips, offset, day, minutes_list[i], conns[i], starts):
                    taken += 1
                    if taken >= per_route:
                        break
            if taken >= per_route:
                break
        if extra_live and trips and origin:
            # the few running vehicles say which trips to look at: no need to scan the timetable
            for offset, day, dtype, _lo, _hi in days:
                by_start, minutes_of = _trips_by_start(origin, dtype), _lookup(table, dtype)
                starts = _lookup(origin, dtype)
                for start in trips:
                    for conn in by_start.get(start, ()):
                        if (ri, conn, offset) not in seen and conn in minutes_of:
                            add(ri, route, trips, offset, day, minutes_of[conn], conn, starts)

    result.sort(key=lambda d: d.expected)
    cutoff = now - timedelta(seconds=30)
    result = [d for d in result if d.expected >= cutoff]
    if not extra_live:
        return result[:limit]
    # the soonest `limit`, plus every live-matched departure after them
    return result[:limit] + [d for d in result[limit:] if d.vehicle_id]

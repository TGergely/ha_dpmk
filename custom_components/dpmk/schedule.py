"""Turn timetables + live vehicles into a list of upcoming departures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
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

    @property
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
    out: dict[tuple[str, str], dict[int, dict]] = {}
    for v in vehicles:
        out.setdefault((str(v["Line"]), str(v["Dir"])), {})[int(v["TripTime"])] = v
    return out


def build_departures(
    routes: list[tuple[Route, Timetable, Timetable | None]],
    vehicles: list[dict],
    now: datetime,
    school_mode: str = SCHOOL_AUTO,
    limit: int = 8,
    stop_name: str | None = None,
    stop_id: str | None = None,
) -> list[Departure]:
    """routes: (route, timetable at the stop, timetable at the line origin)."""
    live = index_vehicles(vehicles)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result: list[Departure] = []
    for route, table, origin in routes:
        trips = live.get((route.line, route.direction), {})
        for offset in (-1, 0, 1):
            day = midnight + timedelta(days=offset)
            dtype = day_type_for(day.date(), school_mode)
            times = table.tables.get(dtype) or []
            starts = dict(origin.tables.get(dtype, [])) if origin else {}
            for conn, minutes in times:
                scheduled = day + timedelta(minutes=minutes)
                if not now - timedelta(minutes=1) <= scheduled <= now + timedelta(hours=26):
                    continue
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
                        route.line,
                        route.line_type,
                        route.destination,
                        scheduled,
                        delay,
                        vehicle_id,
                        stop_name,
                        stop_id,
                    )
                )
    result.sort(key=lambda d: d.expected)
    return [d for d in result if d.expected >= now - timedelta(seconds=30)][:limit]

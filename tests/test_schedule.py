"""The departure builder must give the same answer as the simple reference version below.

The reference is the original, slow algorithm. The shipped one is optimised (sorted tables, bisect,
cached start times); these tests compare both on random timetables, live vehicles, time zones and
the days the clocks change.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.dpmk.api import Route, Timetable
from custom_components.dpmk.schedule import (
    Departure,
    build_departures,
    classify_movement,
    day_type_for,
    index_vehicles,
    nearby_vehicles,
    offset_m,
)

TZ = ZoneInfo("Europe/Bratislava")
DAY_TYPES = ("school", "holidays", "free")


def reference_build_departures(routes, vehicles, now, school_mode="auto", limit=8, stop_name=None, stop_id=None):
    """The original algorithm: expand every conn of every day type, filter, sort."""
    live = index_vehicles(vehicles)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
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
                        route.line, route.line_type, route.destination, scheduled, delay,
                        vehicle_id, stop_name, stop_id,
                    )
                )
    result.sort(key=lambda d: d.expected)
    return [d for d in result if d.expected >= now - timedelta(seconds=30)][:limit]


def make_world(rng: random.Random, n_routes: int = 6):
    """Random routes with timetables for all day types, line-origin start times and live vehicles."""
    routes, vehicles = [], []
    for i in range(n_routes):
        route = Route(
            str(40000 + i),
            str(rng.choice([1, 2, 9, 17, 35, 71, 72, 101])) + ("" if i < 4 else "N"),
            rng.choice("AE"),
            f"Dest {i}",
            "5",
            str(i % 2),
        )
        tables, starts = {}, {}
        for dtype in DAY_TYPES:
            n = rng.choice([0, 3, 40, 120, 200])
            minutes = sorted(rng.sample(range(250, 1560), min(n, 1300)))  # up to 02:00 next day
            tables[dtype] = [(str(j + 1), m) for j, m in enumerate(minutes)]
            starts[dtype] = [(str(j + 1), max(0, m - rng.randint(0, 45))) for j, m in enumerate(minutes)]
        routes.append((route, Timetable([], tables), Timetable([], starts)))
        # running vehicles whose start time matches some trips of this route
        for dtype in DAY_TYPES:
            for _conn, start in rng.sample(starts[dtype], min(len(starts[dtype]), 3)):
                vehicles.append(
                    {
                        "Line": route.line,
                        "Dir": int(route.direction),
                        "Trip": rng.randint(1, 99),
                        "TripTime": start,
                        "Delay": rng.randint(-300, 900),
                        "Lat": 48.7,
                        "Lng": 21.25,
                    }
                )
    return routes, vehicles


# a spread of moments: ordinary days, weekends, public holidays, night hours and both clock changes
MOMENTS = [
    datetime(2026, 10, 23, 0, 0, tzinfo=TZ),
    datetime(2026, 10, 23, 5, 59, tzinfo=TZ),
    datetime(2026, 10, 23, 12, 30, tzinfo=TZ),
    datetime(2026, 10, 23, 23, 59, tzinfo=TZ),
    datetime(2026, 10, 24, 3, 15, tzinfo=TZ),  # Saturday night
    datetime(2026, 10, 25, 1, 30, tzinfo=TZ),  # night the clocks go back (CEST)
    datetime(2026, 10, 25, 3, 30, tzinfo=TZ),  # same night, after the change (CET)
    datetime(2026, 10, 25, 12, 0, tzinfo=TZ),
    datetime(2027, 3, 28, 1, 30, tzinfo=TZ),  # night the clocks go forward
    datetime(2027, 3, 28, 4, 0, tzinfo=TZ),
    datetime(2026, 12, 24, 10, 0, tzinfo=TZ),  # public holiday, school break
    datetime(2026, 7, 15, 9, 0, tzinfo=TZ),  # summer
    datetime(2027, 3, 29, 8, 0, tzinfo=TZ),  # Easter Monday
    datetime(2026, 11, 17, 7, 45, tzinfo=TZ),  # public holiday
]


def as_tuples(deps):
    return [
        (d.line, d.destination, d.scheduled, d.expected, d.delay, d.vehicle_id, d.stop, d.stop_id)
        for d in deps
    ]


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("school_mode", ["auto", "school", "holidays"])
def test_same_answer_as_the_reference(seed, school_mode):
    rng = random.Random(seed)
    routes, vehicles = make_world(rng)
    for now in MOMENTS:
        for limit in (8, 80):
            expected = reference_build_departures(routes, vehicles, now, school_mode, limit, "Stop", "42")
            got = build_departures(routes, vehicles, now, school_mode, limit, "Stop", "42")
            assert as_tuples(got) == as_tuples(expected), (seed, school_mode, now, limit)


def test_departures_are_sorted_and_not_in_the_past():
    routes, vehicles = make_world(random.Random(99))
    now = MOMENTS[2]
    deps = build_departures(routes, vehicles, now, "auto", 80)
    assert deps == sorted(deps, key=lambda d: d.expected)
    assert all(d.expected >= now - timedelta(seconds=30) for d in deps)


def test_live_delay_is_applied_to_the_matching_trip_only():
    route = Route("40035", "35", "A", "Exnarova", "5", "0")
    table = Timetable([], {"school": [("1", 600), ("2", 630)], "holidays": [], "free": []})
    origin = Timetable([], {"school": [("1", 590), ("2", 620)], "holidays": [], "free": []})
    now = datetime(2026, 10, 23, 9, 50, tzinfo=TZ)  # a Friday
    vehicles = [{"Line": "35", "Dir": 0, "Trip": 7, "TripTime": 590, "Delay": 120, "Lat": 0, "Lng": 0}]
    deps = build_departures([(route, table, origin)], vehicles, now, "school", 8)
    assert [(d.scheduled.strftime("%H:%M"), d.delay) for d in deps] == [("10:00", 120), ("10:30", None)]
    assert deps[0].expected - deps[0].scheduled == timedelta(seconds=120)


def test_movement_classification():
    assert classify_movement(None, 100) == "unknown"
    assert classify_movement(100, 200) == "leaving"
    assert classify_movement(200, 100) == "approaching"
    assert classify_movement(100, 105) == "stopped"


def test_nearby_vehicles_filters_by_route_and_radius():
    vehicles = [
        {"Line": "1", "Dir": 0, "Trip": 1, "TripTime": 1, "Delay": 0, "Lat": 48.7200, "Lng": 21.2500},
        {"Line": "1", "Dir": 1, "Trip": 2, "TripTime": 1, "Delay": 0, "Lat": 48.7200, "Lng": 21.2500},  # other direction
        {"Line": "2", "Dir": 0, "Trip": 3, "TripTime": 1, "Delay": 0, "Lat": 48.8000, "Lng": 21.2500},  # too far
    ]
    served = {("1", "0"), ("2", "0")}
    only = nearby_vehicles(vehicles, served, 48.7201, 21.2501, 500)
    assert [v["id"] for v in only] == ["1_1_0"]
    every = nearby_vehicles(vehicles, served, 48.7201, 21.2501, 500, only_served=False)
    assert {(v["id"], v["serves"]) for v in every} == {("1_1_0", True), ("1_2_1", False)}


@pytest.mark.parametrize("seed", range(8))
def test_extra_live_adds_every_matched_departure_and_keeps_the_rest(seed):
    routes, vehicles = make_world(random.Random(seed))
    for now in MOMENTS:
        everything = reference_build_departures(routes, vehicles, now, "auto", 100000)
        soonest = build_departures(routes, vehicles, now, "auto", 8)
        got = build_departures(routes, vehicles, now, "auto", 8, extra_live=True)
        assert as_tuples(got[:8]) == as_tuples(soonest)
        assert as_tuples(got) == as_tuples(everything[:8] + [d for d in everything[8:] if d.vehicle_id])


def test_saved_timetables_read_back_unchanged():
    routes, _ = make_world(random.Random(5))
    for route, table, origin in routes:
        assert Route.from_json(route.to_json()) == route
        assert Timetable.from_json(table.to_json()) == table
        assert Timetable.from_json(origin.to_json()).tables == origin.tables


def test_offset_matches_the_vehicle_offsets():
    lat0, lng0 = 48.72, 21.25
    v = {"Line": "1", "Dir": 0, "Trip": 1, "TripTime": 1, "Delay": 0, "Lat": 48.725, "Lng": 21.255}
    near = nearby_vehicles([v], {("1", "0")}, lat0, lng0, 2000)[0]
    assert (near["dx"], near["dy"]) == offset_m(lat0, lng0, v["Lat"], v["Lng"])

"""The planner must agree with a brute-force version that tries every trip combination."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.dpmk.api import Pattern, parse_line_ids, parse_line_page
from custom_components.dpmk import planner
from custom_components.dpmk.planner import MIN_TRANSFER, Network, plan_route
from custom_components.dpmk.schedule import day_type_for

TZ = ZoneInfo("Europe/Bratislava")
DAY_TYPES = ("school", "holidays", "free")
MOMENTS = [
    datetime(2026, 10, 23, 7, 30, tzinfo=TZ),
    datetime(2026, 10, 23, 23, 40, tzinfo=TZ),
    datetime(2026, 10, 24, 12, 0, tzinfo=TZ),  # Saturday
    datetime(2026, 11, 17, 9, 15, tzinfo=TZ),  # public holiday
    datetime(2026, 10, 25, 1, 30, tzinfo=TZ),  # the night the clocks go back
]


def run(coro):
    return asyncio.run(coro)


def make_world(rng, n_stops=9, n_patterns=7):
    stops = [str(100 + i) for i in range(n_stops)]
    patterns, trips = [], []
    for pi in range(n_patterns):
        seq = rng.sample(stops, rng.randint(3, 7))
        patterns.append(
            Pattern(str(40000 + pi), str(pi + 1), "A", str(pi % 2), f"Dest {pi}",
                    tuple((s, str(k + 1)) for k, s in enumerate(seq)))
        )
        by_type = {}
        for dtype in DAY_TYPES:
            rows = []
            for k in range(rng.choice([0, 6, 30, 60])):
                t, times = rng.randint(240, 1500), []
                for _ in seq:
                    times.append(t)
                    t += rng.randint(1, 6)
                rows.append((f"{pi}-{k}", times))
            by_type[dtype] = rows
        trips.append(by_type)
    return stops, patterns, trips


def make_source(patterns, trips):
    index = {(p.line_id, p.direction): i for i, p in enumerate(patterns)}
    calls = []

    async def source(pattern, stop):
        calls.append((pattern.line_id, stop))
        i = index[(pattern.line_id, pattern.direction)]
        pos = [s for s, _ in pattern.stops].index(stop)
        return {dtype: {trip: times[pos] for trip, times in rows} for dtype, rows in trips[i].items()}

    source.calls = calls
    return source


def signature(connections):
    return [
        (c.depart, c.arrive, tuple((l.pattern.line_id, l.day_offset, l.board, l.alight) for l in c.legs))
        for c in connections
    ]


def reference(patterns, trips, starts, ends, now, school_mode, limit, neighbours=None, start_walk=None, end_walk=None):
    """Every vehicle trip between every pair of stops, then every pairing, then the same filtering."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    earliest, latest = now - timedelta(minutes=1), now + planner.HORIZON
    legs = []
    for pi, pattern in enumerate(patterns):
        ids = [s for s, _ in pattern.stops]
        for offset in (-1, 0, 1):
            day = midnight + timedelta(days=offset)
            for trip, times in trips[pi][day_type_for(day.date(), school_mode)]:
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        legs.append(planner.Leg(pattern, ids[i], ids[j], day + timedelta(minutes=times[i]),
                                                day + timedelta(minutes=times[j]), trip, offset))
    ws = {**(start_walk or {}), **{s: 0 for s in starts}}  # where you can board, with the walk to it
    we = {**(end_walk or {}), **{e: 0 for e in ends}}
    minutes = lambda n: timedelta(minutes=n)
    found = [
        planner.Connection((l,), (), ws[l.board], we[l.alight])
        for l in legs
        if l.board in ws and l.alight in we and earliest + minutes(ws[l.board]) <= l.depart <= latest
    ]
    for l1 in legs:
        if l1.board not in ws or not earliest + minutes(ws[l1.board]) <= l1.depart <= latest:
            continue
        for l2 in legs:
            if l2.alight not in we or l2.pattern is l1.pattern and l2.board == l1.alight:
                continue
            walk = 0 if l2.board == l1.alight else dict(neighbours(l1.alight)).get(l2.board) if neighbours else None
            if walk is None:
                continue
            if l2.depart >= l1.arrive + timedelta(minutes=walk + MIN_TRANSFER) and \
                    earliest - timedelta(hours=1) <= l2.depart <= latest + timedelta(hours=3):
                found.append(planner.Connection((l1, l2), (walk,), ws[l1.board], we[l2.alight]))
    unique = {tuple((l.pattern.line_id, l.trip, l.day_offset, l.board, l.alight) for l in c.legs): c for c in found}
    pool = list(unique.values())
    good = [c for c in pool if not planner._dominated(c, pool)]
    good.sort(key=lambda c: (c.depart, c.arrive, len(c.legs), [(l.pattern.line_id, l.trip, l.board, l.alight) for l in c.legs]))
    return planner.dedupe(good)[:limit]


@pytest.mark.parametrize("seed", range(10))
def test_same_connections_as_brute_force(seed):
    rng = random.Random(seed)
    stops, patterns, trips = make_world(rng)
    network, source = Network(patterns), make_source(patterns, trips)
    a, b = rng.sample(stops, 2)
    for now in MOMENTS:
        for mode in ("auto", "school"):
            want = reference(patterns, trips, {a}, {b}, now, mode, 50)
            got = run(plan_route(network, source, [a], [b], now, mode, 50, transfers="always", max_plans=None))
            assert signature(got) == signature(want), (seed, now, mode)


@pytest.mark.parametrize("seed", range(6))
def test_walking_between_nearby_stops(seed):
    rng = random.Random(100 + seed)
    stops, patterns, trips = make_world(rng)
    near = {s: [(o, rng.randint(1, 5)) for o in rng.sample(stops, 2) if o != s] for s in stops}
    network, source = Network(patterns), make_source(patterns, trips)
    a, b = rng.sample(stops, 2)
    now = MOMENTS[0]
    want = reference(patterns, trips, {a}, {b}, now, "auto", 50, neighbours=lambda s: near[s])
    got = run(plan_route(network, source, [a], [b], now, "auto", 50, neighbours=lambda s: near[s],
                         transfers="always", max_plans=None))
    assert signature(got) == signature(want)


@pytest.mark.parametrize("seed", range(8))
def test_walking_at_the_start_and_the_end(seed):
    rng = random.Random(200 + seed)
    stops, patterns, trips = make_world(rng)
    a, b = rng.sample(stops, 2)
    others = [s for s in stops if s not in (a, b)]
    sw = {s: rng.randint(1, 6) for s in rng.sample(others, 2)}
    ew = {s: rng.randint(1, 6) for s in rng.sample(others, 2)}
    network, source = Network(patterns), make_source(patterns, trips)
    for now in MOMENTS[:3]:
        want = reference(patterns, trips, {a}, {b}, now, "auto", 50, start_walk=sw, end_walk=ew)
        got = run(plan_route(network, source, [a], [b], now, "auto", 50, transfers="always", max_plans=None,
                             start_walk=sw, end_walk=ew))
        assert signature(got) == signature(want), (seed, now)


def walking_world():
    """Line 1 serves only A2 and B (A2 is a short walk from A); line 2 serves A and B but only late."""
    p1 = Pattern("40001", "1", "A", "0", "B", (("A2", "1"), ("B", "2")))
    p2 = Pattern("40002", "2", "A", "0", "B", (("A", "1"), ("B", "2")))
    t1 = [(f"t{k}", [600 + 10 * k, 608 + 10 * k]) for k in range(4)]
    t2 = [("u0", [700, 710])]
    return [p1, p2], [{d: t1 for d in DAY_TYPES}, {d: t2 for d in DAY_TYPES}]


def test_walking_to_a_nearby_stop_gives_a_better_connection():
    patterns, trips = walking_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 50, tzinfo=TZ)
    plain = run(plan_route(network, source, ["A"], ["B"], now, "school", 3))
    walk = run(plan_route(network, source, ["A"], ["B"], now, "school", 3, start_walk={"A2": 4}))
    assert [c.legs[0].pattern.line for c in plain] == ["2"]  # only the late line without walking
    first = walk[0]
    assert first.legs[0].pattern.line == "1" and first.walk_start == 4
    assert first.legs[0].depart.strftime("%H:%M") == "10:00"
    assert first.depart.strftime("%H:%M") == "09:56"  # you set off 4 minutes before the bus
    assert first.arrive.strftime("%H:%M") == "10:08"
    # too far to walk in time: the 10:00 bus leaves before you get there
    late = datetime(2026, 10, 23, 9, 58, tzinfo=TZ)
    assert run(plan_route(network, source, ["A"], ["B"], late, "school", 1, start_walk={"A2": 4}))[0].legs[0].depart.strftime("%H:%M") == "10:10"


def test_walking_at_the_end_counts_in_the_arrival():
    patterns, trips = walking_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 50, tzinfo=TZ)
    # the destination is B2, 3 minutes' walk from B, and no line serves B2
    got = run(plan_route(network, source, ["A2"], ["B2"], now, "school", 2, end_walk={"B": 3}))
    assert got[0].walk_end == 3 and got[0].arrive.strftime("%H:%M") == "10:11"


def test_walking_is_not_tried_when_there_are_enough_connections():
    patterns, trips = walking_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 50, tzinfo=TZ)
    got = run(plan_route(network, source, ["A2"], ["B"], now, "school", 3, start_walk={"A": 4}))
    assert len(got) == 3 and all(c.walk_start == 0 for c in got)  # line 1 itself gives three
    assert {line for line, _ in source.calls} == {"40001"}


def test_several_poles_of_one_stop():
    rng = random.Random(3)
    stops, patterns, trips = make_world(rng)
    network, source = Network(patterns), make_source(patterns, trips)
    now = MOMENTS[0]
    want = reference(patterns, trips, set(stops[:2]), set(stops[-2:]), now, "auto", 50)
    got = run(plan_route(network, source, stops[:2], stops[-2:], now, "auto", 50, transfers="always", max_plans=None))
    assert signature(got) == signature(want)


def line_world(times_direct=4):
    """Stops A-B-C on line 1 (several trips) and B-D on line 2, so A to D needs a change at B."""
    p1 = Pattern("40001", "1", "A", "0", "C", (("A", "1"), ("B", "2"), ("C", "3")))
    p2 = Pattern("40002", "2", "A", "0", "D", (("B", "1"), ("D", "2")))
    t1 = [(f"t{k}", [600 + 10 * k, 605 + 10 * k, 610 + 10 * k]) for k in range(times_direct)]
    t2 = [(f"u{k}", [607 + 10 * k, 615 + 10 * k]) for k in range(times_direct)]
    trips = [{d: t1 for d in DAY_TYPES}, {d: t2 for d in DAY_TYPES}]
    return [p1, p2], trips


def test_change_is_found_and_respects_the_minimum_time():
    patterns, trips = line_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 55, tzinfo=TZ)
    got = run(plan_route(network, source, ["A"], ["D"], now, "school", 3))
    first = got[0]
    assert [l.pattern.line for l in first.legs] == ["1", "2"]
    # line 1 arrives at B 10:05, so the 10:07 departure is exactly MIN_TRANSFER later: just possible
    assert first.legs[1].depart - first.legs[0].arrive >= timedelta(minutes=MIN_TRANSFER)
    assert first.arrive.strftime("%H:%M") == "10:15"
    assert first.transfers == 1


def test_direct_trips_skip_the_search_for_changes():
    patterns, trips = line_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 55, tzinfo=TZ)
    got = run(plan_route(network, source, ["A"], ["C"], now, "school", 3))
    assert len(got) == 3 and all(c.transfers == 0 for c in got)
    assert {line for line, _ in source.calls} == {"40001"}  # line 2 was never looked at


def test_transfers_never_and_unreachable():
    patterns, trips = line_world()
    network, source = Network(patterns), make_source(patterns, trips)
    now = datetime(2026, 10, 23, 9, 55, tzinfo=TZ)
    assert run(plan_route(network, source, ["A"], ["D"], now, "school", 3, transfers="never")) == []
    assert run(plan_route(network, source, ["D"], ["A"], now, "school", 3)) == []  # lines only go one way
    assert run(plan_route(network, source, ["A"], ["Z"], now, "school", 3)) == []  # unknown stop


def test_a_trip_that_runs_past_midnight():
    p = Pattern("40001", "N1", "A", "0", "C", (("A", "1"), ("B", "2")))
    # 23:58 at A, and at B the table says 00:03 (3 minutes) instead of 1443
    tables = {d: [("t1", [1438, 3])] for d in DAY_TYPES}

    async def source(pattern, stop):
        pos = 0 if stop == "A" else 1
        return {d: {"t1": tables[d][0][1][pos]} for d in tables}

    now = datetime(2026, 10, 23, 23, 50, tzinfo=TZ)
    got = run(plan_route(Network([p]), source, ["A"], ["B"], now, "school", 3))
    assert len(got) == 1 and got[0].arrive - got[0].depart == timedelta(minutes=5)


def test_at_most_a_dozen_line_pairs_are_looked_up():
    rng = random.Random(5)
    stops, patterns, trips = make_world(rng, n_stops=12, n_patterns=14)
    network = Network(patterns)
    for a in stops[:4]:
        for b in stops[-4:]:
            assert len(network.candidates([a], [b], transfers=True)) <= 12 + len(network.candidates([a], [b], transfers=False))


def test_last_stop_is_added_from_the_timetable_page():
    # the line page leaves out the last stop; the timetable page lists all of them
    p = Pattern("40101", "N1", "A", "1", "Madridská", (("229", "2"), ("55", "3"), ("94", "16")))
    page = [("229", "2"), ("55", "3"), ("94", "16"), ("85", "19")]
    assert p.completed(page).stops == p.stops + (("85", "19"),)
    assert p.completed(page[:3]) is p  # nothing more to add
    assert p.completed([("1", "1")] + page) is p  # a page that does not continue the pattern is ignored
    assert p.completed(page).destination == "Madridská"


def test_arrival_at_the_last_stop_is_estimated():
    previous = {"free": {"a": 100, "b": 130}, "school": {"a": 105}}
    before = {"free": {"a": 97, "b": 126}, "school": {"a": 104}}  # gaps 3, 4, 1 -> median 3
    assert planner.estimate_arrivals(previous, before) == {"free": {"a": 103, "b": 133}, "school": {"a": 108}}
    assert planner.estimate_arrivals(previous, None) == {"free": {"a": 102, "b": 132}, "school": {"a": 107}}
    far = {"free": {"a": 50, "b": 50}}  # a gap of 50 minutes is not believed: at most 5
    assert planner.estimate_arrivals({"free": {"a": 100}}, far)["free"]["a"] == 105
    assert planner.estimate_arrivals({"free": {"a": 100}}, {"free": {"a": 100}})["free"]["a"] == 102  # no usable gap


def test_a_trip_to_the_last_stop_is_found_with_an_estimated_arrival():
    p = Pattern("40101", "N1", "A", "1", "End", (("A", "1"), ("B", "2"), ("C", "3"), ("D", "4")))
    at = {"A": 1500, "B": 1505, "C": 1509}  # 01:00 of the next day, so the trip belongs to this service day

    async def source(pattern, stop):
        if stop in at:
            return {d: {"t1": at[stop]} for d in DAY_TYPES}
        return planner.estimate_arrivals(await source(pattern, "C"), await source(pattern, "B"))  # D has no page

    now = datetime(2026, 10, 23, 23, 30, tzinfo=TZ)
    got = run(plan_route(Network([p]), source, ["A"], ["D"], now, "school", 3))
    assert len(got) == 1 and got[0].arrive - got[0].depart == timedelta(minutes=13)  # 1509 + gap 4 = 1513


LINE_PAGE = """
<h1>Linka <span class="line line--type-A line--name-35">35</span></h1>
<table><thead><tr><th><i></i>Staré mesto, Nám. osloboditeľov</th></tr></thead><tbody>
<tr><td><a href="/cp/linka/40035/32/2/1">Exnárova</a></td></tr>
<tr><td><a href="/cp/linka/40035/150/3/1">Heringeš</a></td></tr></tbody></table>
<table><thead><tr><th><i></i>Darg. hrdinov, Exnárova</th></tr></thead><tbody>
<tr><td><a href="/cp/linka/40035/113/16/0">Nám. osloboditeľov</a></td></tr>
<tr><td><a href="/cp/linka/40035/150/3/0">Heringeš</a></td></tr></tbody></table>
"""


def test_line_page_and_line_list_are_read():
    a, b = parse_line_page(LINE_PAGE, "40035")
    assert (a.line, a.line_type, a.direction, a.destination) == ("35", "A", "1", "Staré mesto, Nám. osloboditeľov")
    assert a.stops == (("32", "2"), ("150", "3"))
    assert (b.direction, b.stops[0], b.stops[-1]) == ("0", ("113", "16"), ("150", "3"))
    assert Pattern.from_json(a.to_json()) == a
    assert parse_line_ids('<a href="/cp/linka/40002">x</a><a href="/cp/linka/40001">y</a><a href="/cp/linka/40001/5/1/0">z</a>') == ["40001", "40002"]

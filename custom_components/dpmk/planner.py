"""Route planning between two stops: direct trips, and trips with one change.

The network (which stops each line direction serves, in order) comes from the line pages. Times come
from the timetable pages, fetched only for the few lines and stops a search needs.
"""

from __future__ import annotations

import asyncio
from bisect import bisect_left
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .api import Pattern
from .const import SCHOOL_AUTO
from .schedule import day_type_for

MIN_TRANSFER = 2  # minutes needed to change between two vehicles at the same stop
WALK_METERS_PER_MINUTE = 70
MAX_TRANSFER_PLANS = 12  # candidate line pairs whose times are looked up in one search
HORIZON = timedelta(hours=6)  # how far ahead a search looks for departures
DIRECT_ENOUGH = 3  # with this many direct trips, no trips with a change are looked for

# {day type: {trip id: minutes since midnight}} for one pattern at one stop
Tables = dict[str, dict[str, int]]
TableSource = Callable[[Pattern, str], Awaitable[Tables]]
Neighbours = Callable[[str], list[tuple[str, int]]]  # stop id -> [(nearby stop id, walking minutes)]


TERMINUS_GAP = 2  # minutes from the one-before-last stop to the last, when it cannot be worked out


def estimate_arrivals(previous: Tables, before: Tables | None = None) -> Tables:
    """Arrival times at the last stop of a line direction, which DPMK does not publish.

    It is the time at the stop before it plus the usual gap, taken from the two stops before that
    (the median over all trips, kept between 1 and 5 minutes).
    """
    gaps = sorted(
        m - before[dtype][trip]
        for dtype, rows in previous.items()
        for trip, m in rows.items()
        if before and trip in before.get(dtype, {}) and m > before[dtype][trip]
    )
    gap = min(5, max(1, gaps[len(gaps) // 2])) if gaps else TERMINUS_GAP
    return {dtype: {trip: m + gap for trip, m in rows.items()} for dtype, rows in previous.items()}


@dataclass(frozen=True)
class Leg:
    pattern: Pattern
    board: str  # stop id
    alight: str
    depart: datetime
    arrive: datetime
    trip: str  # trip id of this line (the same on every stop page of the trip)
    day_offset: int  # which service day it belongs to: -1 yesterday, 0 today, 1 tomorrow


@dataclass(frozen=True)
class Connection:
    legs: tuple[Leg, ...]
    walk: tuple[int, ...]  # minutes walked between leg i and leg i+1
    walk_start: int = 0  # minutes walked from where you start to the first stop
    walk_end: int = 0  # minutes walked from the last stop to where you are going

    @property
    def depart(self) -> datetime:
        """When you set off: the first vehicle's departure, less the walk to its stop."""
        return self.legs[0].depart - timedelta(minutes=self.walk_start)

    @property
    def arrive(self) -> datetime:
        """When you are there: the last vehicle's arrival, plus the walk to the destination."""
        return self.legs[-1].arrive + timedelta(minutes=self.walk_end)

    @property
    def transfers(self) -> int:
        return len(self.legs) - 1


@dataclass(frozen=True)
class Plan:
    """Which lines to take, before any times are known."""

    legs: tuple[tuple[int, str, str], ...]  # (pattern index, board stop, alight stop)
    walk: tuple[int, ...]
    cost: int  # stops travelled plus walking minutes: only used to rank candidates


class Network:
    """Every line direction and where it stops."""

    def __init__(self, patterns: list[Pattern]) -> None:
        self.patterns = list(patterns)
        self.positions: list[dict[str, list[int]]] = []
        self.at: dict[str, list[int]] = {}  # stop id -> pattern indexes
        for index, pattern in enumerate(self.patterns):
            where: dict[str, list[int]] = {}
            for position, (stop, _seq) in enumerate(pattern.stops):
                where.setdefault(stop, []).append(position)
            self.positions.append(where)
            for stop in where:
                self.at.setdefault(stop, []).append(index)

    def stop_ids(self, index: int) -> list[str]:
        return [stop for stop, _ in self.patterns[index].stops]

    def after(self, index: int, stop: str, start: str) -> int | None:
        """The first position of `stop` after the first position of `start` on a pattern."""
        starts = self.positions[index].get(start)
        if not starts:
            return None
        first = starts[0]
        return next((p for p in self.positions[index].get(stop, ()) if p > first), None)

    def candidates(
        self,
        starts: list[str],
        ends: list[str],
        transfers: bool,
        neighbours: Neighbours | None = None,
        max_plans: int | None = MAX_TRANSFER_PLANS,
        walk_start: dict[str, int] | None = None,
        walk_end: dict[str, int] | None = None,
    ) -> list[Plan]:
        """Line combinations from any of `starts` to any of `ends`, cheapest first.

        walk_start / walk_end: minutes of walking to reach a start stop, or from an end stop (only
        used to rank the candidates; the times are worked out in combine()).
        """
        ws, we = walk_start or {}, walk_end or {}
        plans: dict[tuple, Plan] = {}
        for a in starts:
            for p1 in self.at.get(a, ()):
                ids1 = self.stop_ids(p1)
                first = self.positions[p1][a][0]
                for b in ends:
                    pb = self.after(p1, b, a)
                    if pb is not None:
                        key = ((p1, a, b),)
                        plans[key] = Plan(key, (), pb - first + ws.get(a, 0) + we.get(b, 0))
                if not transfers:
                    continue
                for j in range(first + 1, len(ids1)):
                    x1 = ids1[j]
                    hops = [(x1, 0)] + (list(neighbours(x1)) if neighbours else [])
                    for x2, walk in hops:
                        for p2 in self.at.get(x2, ()):
                            if p2 == p1 and walk == 0:
                                continue
                            for b in ends:
                                pb = self.after(p2, b, x2)
                                if pb is None:
                                    continue
                                key = ((p1, a, x1), (p2, x2, b))
                                cost = (j - first) + (pb - self.positions[p2][x2][0]) + walk + ws.get(a, 0) + we.get(b, 0)
                                plans[key] = Plan(key, (walk,), cost)
        direct = sorted((p for p in plans.values() if len(p.legs) == 1), key=lambda p: p.cost)
        changing = sorted((p for p in plans.values() if len(p.legs) == 2), key=lambda p: p.cost)
        if max_plans is not None:
            changing = changing[:max_plans]
        return direct + changing


def _service_days(now: datetime, school_mode: str) -> list[tuple[int, datetime, str]]:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for offset in (-1, 0, 1):
        day = midnight + timedelta(days=offset)
        out.append((offset, day, day_type_for(day.date(), school_mode)))
    return out


def _trips(
    pattern: Pattern,
    board: str,
    alight: str,
    board_table: Tables,
    alight_table: Tables,
    days: list[tuple[int, datetime, str]],
    earliest: datetime,
    latest: datetime,
) -> list[Leg]:
    """Every trip of a pattern from `board` to `alight` that leaves between earliest and latest."""
    legs = []
    for offset, day, dtype in days:
        arrivals = alight_table.get(dtype, {})
        for trip, t_board in board_table.get(dtype, {}).items():
            t_alight = arrivals.get(trip)
            if t_alight is None:
                continue
            if t_alight < t_board and t_board > 1200:  # the trip runs past midnight
                t_alight += 1440
            if t_alight <= t_board:
                continue
            depart = day + timedelta(minutes=t_board)
            if earliest <= depart <= latest:
                legs.append(Leg(pattern, board, alight, depart, day + timedelta(minutes=t_alight), trip, offset))
    legs.sort(key=lambda leg: leg.depart)
    return legs


def _dominated(c: Connection, others: list[Connection]) -> bool:
    return any(
        o is not c
        and o.depart >= c.depart
        and o.arrive <= c.arrive
        and (o.depart > c.depart or o.arrive < c.arrive or len(o.legs) < len(c.legs))
        for o in others
    )


def combine(
    network: Network,
    plans: list[Plan],
    tables: dict[tuple[int, str], Tables],
    now: datetime,
    school_mode: str = SCHOOL_AUTO,
    limit: int = 5,
    walk_start: dict[str, int] | None = None,
    walk_end: dict[str, int] | None = None,
) -> list[Connection]:
    """Turn plans plus timetables into connections: the useful ones, soonest first.

    walk_start / walk_end: minutes to walk from where you start to a stop, and from a stop to where
    you are going. You must reach the first stop in time, and the arrival includes the last walk.
    """
    days = _service_days(now, school_mode)
    earliest, latest = now - timedelta(minutes=1), now + HORIZON
    ws, we = walk_start or {}, walk_end or {}
    found: list[Connection] = []
    for plan in plans:
        if len(plan.legs) == 1:
            index, a, b = plan.legs[0]
            wa, wb = ws.get(a, 0), we.get(b, 0)
            for leg in _trips(
                network.patterns[index], a, b, tables[(index, a)], tables[(index, b)], days,
                earliest + timedelta(minutes=wa), latest,
            ):
                found.append(Connection((leg,), (), wa, wb))
            continue
        (i1, a, x1), (i2, x2, b) = plan.legs
        walk = plan.walk[0]
        wa, wb = ws.get(a, 0), we.get(b, 0)
        first = _trips(
            network.patterns[i1], a, x1, tables[(i1, a)], tables[(i1, x1)], days,
            earliest + timedelta(minutes=wa), latest,
        )
        second = _trips(
            network.patterns[i2], x2, b, tables[(i2, x2)], tables[(i2, b)], days,
            earliest - timedelta(hours=1), latest + timedelta(hours=3),
        )
        departs = [leg.depart for leg in second]
        # best[k]: among second[k:], the trip that arrives first (the earlier departure on a tie)
        best: list[int] = [0] * len(second)
        for k in range(len(second) - 1, -1, -1):
            best[k] = k if k == len(second) - 1 or second[k].arrive <= second[best[k + 1]].arrive else best[k + 1]
        for leg in first:
            ready = leg.arrive + timedelta(minutes=walk + MIN_TRANSFER)
            k = bisect_left(departs, ready)
            if k < len(second):
                found.append(Connection((leg, second[best[k]]), (walk,), wa, wb))
    # the same vehicles reached by two plans count once
    unique = {
        tuple((l.pattern.line_id, l.pattern.direction, l.trip, l.day_offset, l.board, l.alight) for l in c.legs): c
        for c in found
    }
    pool = list(unique.values())
    good = [c for c in pool if not _dominated(c, pool)]
    good.sort(key=lambda c: (c.depart, c.arrive, len(c.legs), [(l.pattern.line_id, l.trip, l.board, l.alight) for l in c.legs]))
    return dedupe(good)[:limit]


def dedupe(sorted_connections: list[Connection]) -> list[Connection]:
    """The same lines at the same times are one connection for a traveller (whatever stop they change at)."""
    seen, out = set(), []
    for c in sorted_connections:
        key = (c.depart, c.arrive, tuple((l.pattern.line_id, l.day_offset) for l in c.legs))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


async def plan_route(
    network: Network,
    source: TableSource,
    starts: list[str],
    ends: list[str],
    now: datetime,
    school_mode: str = SCHOOL_AUTO,
    limit: int = 5,
    neighbours: Neighbours | None = None,
    transfers: str = "auto",  # "auto": only when there are few direct trips | "always" | "never"
    max_plans: int | None = MAX_TRANSFER_PLANS,
    concurrency: int = 3,
    start_walk: dict[str, int] | None = None,
    end_walk: dict[str, int] | None = None,
) -> list[Connection]:
    """The next connections from one of `starts` to one of `ends` (a stop can have several poles).

    start_walk / end_walk: other stops you could walk to at the start, or from at the end, with the
    minutes it takes. They are looked at only when the plain search finds fewer than DIRECT_ENOUGH
    connections (or with transfers="always").
    """
    sem = asyncio.Semaphore(concurrency)
    tables: dict[tuple[int, str], Tables] = {}

    async def fetch(plans: list[Plan]) -> None:
        wanted = {(i, s) for plan in plans for (i, a, b) in plan.legs for s in (a, b)} - set(tables)

        async def one(index: int, stop: str) -> None:
            async with sem:
                tables[(index, stop)] = await source(network.patterns[index], stop)

        await asyncio.gather(*(one(i, s) for i, s in sorted(wanted)))

    direct = network.candidates(starts, ends, transfers=False)
    await fetch(direct)
    found = combine(network, direct, tables, now, school_mode, limit)
    walking = bool(start_walk or end_walk)
    if (transfers == "never" and not walking) or (transfers == "auto" and len(found) >= DIRECT_ENOUGH):
        return found
    # the walks, with the stops you named themselves at no walk
    ws = {**(start_walk or {}), **{s: 0 for s in starts}}
    we = {**(end_walk or {}), **{e: 0 for e in ends}}
    every = network.candidates(
        list(ws), list(we), transfers=transfers != "never", neighbours=neighbours, max_plans=max_plans,
        walk_start=ws, walk_end=we,
    )
    await fetch(every)
    return combine(network, every, tables, now, school_mode, limit, ws, we)

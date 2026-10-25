"""The bundled list of DPMK stops (data/stops.json) and helpers to find stops by position.

The list is built offline by tools/build_stops.py and shipped with the integration, so adding a
stop needs no request to dpmk.sk. Coordinates come from the city's open data (CC BY 4.0).
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .schedule import distance_m

DATA_FILE = Path(__file__).parent / "data" / "stops.json"
NEAR_CITY_M = 30_000  # a home farther than this from every stop gets an alphabetical list


@dataclass(frozen=True)
class StopInfo:
    stop_id: str
    label: str  # "Name - District", as dpmk.sk writes it
    name: str
    district: str
    lat: float | None = None
    lng: float | None = None
    poles: tuple[tuple[float, float], ...] = ()  # one point per physical stop pole

    @property
    def has_position(self) -> bool:
        return self.lat is not None and self.lng is not None

    def distance_to(self, lat: float, lng: float) -> float | None:
        """Metres to the nearest pole of this stop (the stop may have poles on both sides of a road)."""
        points = self.poles or (((self.lat, self.lng),) if self.has_position else ())
        if not points:
            return None
        return min(distance_m(lat, lng, p[0], p[1]) for p in points)


def sort_key(text: str) -> str:
    return unicodedata.normalize("NFKD", text).casefold()


@dataclass(frozen=True)
class Catalog:
    generated: str
    stops: dict[str, StopInfo]

    def get(self, stop_id: str) -> StopInfo | None:
        return self.stops.get(str(stop_id))

    def near(self, lat: float, lng: float, radius: float) -> list[tuple[StopInfo, float]]:
        """Stops with a pole within `radius` metres, nearest first."""
        found = []
        for stop in self.stops.values():
            d = stop.distance_to(lat, lng)
            if d is not None and d <= radius:
                found.append((stop, d))
        return sorted(found, key=lambda item: item[1])

    def sorted_for(self, lat: float, lng: float) -> list[tuple[StopInfo, float | None]]:
        """Every stop for a pick list: nearest first when the position is in town, else A to Z.

        In the nearest-first order, stops without coordinates come last.
        """
        with_distance = [(s, s.distance_to(lat, lng)) for s in self.stops.values()]
        known = [d for _, d in with_distance if d is not None]
        if known and min(known) <= NEAR_CITY_M:
            return sorted(
                with_distance,
                key=lambda item: (item[1] is None, item[1] or 0, sort_key(item[0].label)),
            )
        return sorted(((s, None) for s, _ in with_distance), key=lambda item: sort_key(item[0].label))


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    """Read data/stops.json (blocking: call it in an executor). Cached after the first read."""
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    stops = {}
    for item in raw["stops"]:
        stops[item["id"]] = StopInfo(
            stop_id=item["id"],
            label=item["label"],
            name=item["name"],
            district=item["district"],
            lat=item.get("lat"),
            lng=item.get("lng"),
            poles=tuple((p[0], p[1]) for p in item.get("poles", [])),
        )
    return Catalog(generated=raw.get("generated", ""), stops=stops)

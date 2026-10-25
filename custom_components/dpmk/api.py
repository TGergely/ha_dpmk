"""Client and parsers for the public dpmk.sk timetable pages and live feed."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

import aiohttp

from .const import BASE_URL

HEADERS = {"User-Agent": "Mozilla/5.0 (Home Assistant dpmk integration)"}
TIMEOUT = aiohttp.ClientTimeout(total=20)


@dataclass(frozen=True)
class Route:
    """One line in one direction serving a stop."""

    line_id: str
    line: str
    line_type: str
    destination: str
    seq: str
    direction: str

    @property
    def key(self) -> str:
        return f"{self.line_id}_{self.direction}"


@dataclass
class Stop:
    stop_id: str
    name: str
    routes: list[Route] = field(default_factory=list)


@dataclass
class Timetable:
    """Parsed line page: stops in travel order and times per day type."""

    stops: list[tuple[str, str]]  # (stop_id, seq), first = origin
    tables: dict[str, list[tuple[str, int]]]  # day type -> [(conn_id, minutes)]


def _strip(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def day_type(label: str) -> str:
    """Classify a timetable header into school / holidays / free."""
    norm = unicodedata.normalize("NFKD", label.lower())
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    if "prazdn" in norm:
        return "holidays"
    if "volne" in norm or "sobot" in norm or "nedel" in norm:
        return "free"
    return "school"


def parse_stop_page(html: str, stop_id: str) -> Stop:
    m = re.search(r"<h1[^>]*>\s*Zast[^<]*?\s(.*?)</h1>", html, re.S)
    name = _strip(m.group(1)) if m else stop_id
    routes: list[Route] = []
    for row in re.split(r"<tr\b", html)[1:]:
        r = re.search(
            r'line--type-(\w+) line--name-([^"]+)".*?'
            r'href="/cp/linka/(\d+)/\d+/(\d+)/(\d)">(.*?)</a>',
            row,
            re.S,
        )
        if r:
            routes.append(
                Route(r.group(3), r.group(2), r.group(1), _strip(r.group(6)), r.group(4), r.group(5))
            )
    return Stop(stop_id, name, routes)


def parse_timetable(html: str) -> Timetable:
    stops = re.findall(r'<tr\s+data-id="(\d+)_(\d+)"', html)
    tables: dict[str, list[tuple[str, int]]] = {}
    parts = html.split('cp-table--time"')[1:]
    for part in parts:
        table = part.split("</table>")[0]
        th = re.search(r"<th[^>]*>(.*?)</th>", table, re.S)
        dtype = day_type(_strip(th.group(1))) if th else "school"
        times = []
        for conn, raw in re.findall(r'data-conn-id="(\d+)"\s+data-time="(\d+)"', table):
            n = int(raw)
            times.append((conn, (n // 100) * 60 + n % 100))
        tables[dtype] = times
    return Timetable(stops, tables)


def parse_line_colors(css: str) -> dict[str, dict[str, str]]:
    """Read per-line badge colours from DPMK's stylesheet (later rules override)."""
    colors: dict[str, dict[str, str]] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        names = re.findall(r"(?<![\w-])\.line--name-([\w]+)", selectors)
        if not names or "h1" in selectors:
            continue
        for prop, value in re.findall(r"(?<![\w-])(color|background-color|background)\s*:\s*([^;!]+)", body):
            key = "fg" if prop == "color" else "bg"
            for name in names:
                colors.setdefault(name, {})[key] = value.strip()
    return colors


class DpmkApi:
    """Thin async client for dpmk.sk."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str, **params) -> aiohttp.ClientResponse:
        resp = await self._session.get(
            BASE_URL + path, params=params or None, headers=HEADERS, timeout=TIMEOUT
        )
        resp.raise_for_status()
        return resp

    async def list_stops(self) -> dict[str, str]:
        """Every stop as {stop_id: label}, e.g. {"42": "Hlavná pošta - Staré mesto"}.

        The site only offers a search box, but every label carries its district after " - ",
        so asking for "-" returns all stops at once. If that ever stops working, the vowels
        together cover practically every name.
        """
        found: dict[str, str] = {}
        for term in ("-", "a", "e", "o", "i"):
            resp = await self._get("/search/autocomplete", term=term)
            for item in await resp.json(content_type=None):
                value = item.get("value", "")
                if value.startswith("stop_"):
                    found[value[5:]] = item["label"]
            if len(found) >= 100:  # "-" normally returns the lot, no need to ask more
                break
        return found

    async def get_stop(self, stop_id: str) -> Stop:
        resp = await self._get(f"/cp/zastavka/{stop_id}")
        return parse_stop_page(await resp.text(), stop_id)

    async def get_timetable(self, route: Route, stop_id: str, seq: str | None = None) -> Timetable:
        resp = await self._get(
            f"/cp/linka/{route.line_id}/{stop_id}/{seq or route.seq}/{route.direction}"
        )
        return parse_timetable(await resp.text())

    async def get_line_types(self) -> dict[str, str]:
        """{line: 'A' (bus) | 'E' (tram)} for every line, from the config of DPMK's map page."""
        resp = await self._get("/cp/mapa")
        m = re.search(r'id="vue-app-config">(.*?)</script>', await resp.text(), re.S)
        lines = json.loads(m.group(1)).get("lines", {}) if m else {}
        return {name: info.get("type", "A") for name, info in lines.items()}

    async def get_line_colors(self) -> dict[str, dict[str, str]]:
        resp = await self._get("/themes/dpmk/assets/dist/css/dpmk.styles.css")
        return parse_line_colors(await resp.text())

    async def get_vehicles(self) -> list[dict]:
        resp = await self._get("/api/cp/map")
        return await resp.json(content_type=None)

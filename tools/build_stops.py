#!/usr/bin/env python3
"""Rebuild custom_components/dpmk/data/stops.json.

Joins two public sources (needs the internet, run it by hand before a release):
  * dpmk.sk            every stop (id and "Name - District" label), via the site's search
  * opendata.kosice.sk "Zastavky MHD" (CC BY 4.0): one point per physical stop pole, with coordinates

A DPMK stop usually covers several poles (one per direction), so each stop gets its poles and the
centroid. Names are matched by normalised name + district, then by similarity; the few that still
differ are listed in ALIASES. Run:  python tools/build_stops.py [--report]
"""
from __future__ import annotations

import collections
import datetime as dt
import difflib
import json
import math
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

DPMK = "https://www.dpmk.sk"
POLES = (
    "https://services-eu1.arcgis.com/qrtO0RIRViAdEN4F/arcgis/rest/services/zastavky_mhd/"
    "FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=json"
)
OUT = Path(__file__).resolve().parent.parent / "custom_components" / "dpmk" / "data" / "stops.json"

# Stops whose names differ between the two sources beyond what the automatic matching can bridge.
# Keys and values are written through norm(): lower case, no accents, punctuation as spaces.
# DPMK label -> (open-data name, open-data district)
ALIASES: dict[str, tuple[str, str]] = {
    "bytovy podnik mesta kosice vysne opatske": ("bytovy podnik", "vysne opatske"),
    "dargovskych hrdinov miu darg hrdinov": ("darg hrdinov miu", "dargovskych hrdinov"),
    "moldavska obchodne centra zapad": ("moldavska oc", "zapad"),
    "vstupny areal nippon steel saca": ("vstup areal uss", "saca"),
    "valcovne nippon steel saca": ("valcovne u s steel", "saca"),
    "vratnica 4 nippon steel saca": ("vratnica 4 u s steel", "saca"),
    "stavadlo 2 nippon steel saca": ("stavadlo 2 u s steel", "saca"),
    "centralne prekladisko rud saca": ("cent prekl rud uss", "saca"),
}


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "ha-dpmk stop list builder"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    for ch in ".,()/-":
        text = text.replace(ch, " ")
    return " ".join(text.split())


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * 111200, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


def dpmk_stops() -> dict[str, str]:
    stops: dict[str, str] = {}
    for item in fetch(f"{DPMK}/search/autocomplete?term=" + urllib.parse.quote("-")):
        if item["value"].startswith("stop_"):
            stops[item["value"][5:]] = item["label"]
    return stops


def pole_groups() -> dict[tuple[str, str], list[tuple[float, float]]]:
    groups: dict[tuple[str, str], list[tuple[float, float]]] = collections.defaultdict(list)
    for f in fetch(POLES)["features"]:
        a, g = f["attributes"], f.get("geometry") or {}
        if g.get("x") is None:
            continue
        district = (a["mestska_cast"] or "").split(" - ")[-1]
        groups[(a["zastavka_nazov"], district)].append((round(g["y"], 6), round(g["x"], 6)))
    return groups


def match(label: str, groups) -> tuple[tuple[str, str] | None, str]:
    name, _, district = label.rpartition(" - ")
    by_norm = {(norm(n), norm(d)): (n, d) for (n, d) in groups}
    if norm(label) in ALIASES and ALIASES[norm(label)] in by_norm:
        return by_norm[ALIASES[norm(label)]], "alias"
    if (norm(name), norm(district)) in by_norm:
        return by_norm[(norm(name), norm(district))], "exact"
    same_name = [k for k in groups if norm(k[0]) == norm(name)]
    if same_name:
        best = max(same_name, key=lambda k: difflib.SequenceMatcher(None, norm(k[1]), norm(district)).ratio())
        return best, "same name, district differs"
    def score(k):
        d = difflib.SequenceMatcher(None, norm(k[1]), norm(district)).ratio()
        n = difflib.SequenceMatcher(None, norm(k[0]), norm(name)).ratio()
        return n if d >= 0.6 else 0
    best = max(groups, key=score)
    if score(best) >= 0.85:
        return best, f"similar name ({score(best):.2f})"
    return None, "no match"


def main_cluster(poles: list[tuple[float, float]], link: float = 350) -> tuple[list[tuple[float, float]], int]:
    """Poles of the biggest group of poles that lie within `link` metres of each other.

    Returns (poles, number_of_groups). If two groups are equally big the stop cannot be placed:
    returns ([], groups).
    """
    clusters: list[list[tuple[float, float]]] = []
    for p in poles:
        near = [c for c in clusters if any(metres(p, q) <= link for q in c)]
        merged = [p] + [q for c in near for q in c]
        clusters = [c for c in clusters if c not in near] + [merged]
    clusters.sort(key=len, reverse=True)
    if len(clusters) > 1 and len(clusters[0]) == len(clusters[1]):
        return [], len(clusters)
    return clusters[0], len(clusters)


def build(report: bool = False) -> dict:
    stops, groups = dpmk_stops(), pole_groups()
    out, notes = [], []
    for stop_id, label in sorted(stops.items(), key=lambda kv: int(kv[0])):
        name, _, district = label.rpartition(" - ")
        key, how = match(label, groups)
        poles = sorted(set(groups[key])) if key else []
        spread = max((metres(a, b) for a in poles for b in poles), default=0)
        if spread > 600:  # same name twice in one district: keep the larger group of poles
            poles, n = main_cluster(poles)
            notes.append((label, key, f"{n} separate places, " + ("kept the larger" if poles else "tie, left without coordinates"), round(spread)))
        elif how != "exact":
            notes.append((label, key, how, round(spread)))
        entry = {"id": stop_id, "label": label, "name": name, "district": district}
        if poles:
            entry["lat"] = round(sum(p[0] for p in poles) / len(poles), 6)
            entry["lng"] = round(sum(p[1] for p in poles) / len(poles), 6)
            entry["poles"] = [list(p) for p in poles]
        out.append(entry)
    if report:
        for n in notes:
            print(n)
    return {
        "generated": dt.date.today().isoformat(),
        "sources": {
            "stops": f"{DPMK} (stop list)",
            "coordinates": "Mesto Kosice open data, 'Zastavky MHD', CC BY 4.0, https://opendata.kosice.sk",
        },
        "stops": out,
    }


if __name__ == "__main__":
    data = build(report="--report" in sys.argv)
    with_coords = sum(1 for s in data["stops"] if "lat" in s)
    print(f"{len(data['stops'])} stops, {with_coords} with coordinates", file=sys.stderr)
    if "--dry" not in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"written {OUT}", file=sys.stderr)

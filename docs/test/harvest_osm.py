#!/usr/bin/env python3
"""Собирает независимые координатные свидетельства OpenStreetMap.

Канонические координаты не меняются. Результат используется как второй слой:
совпадение имени + расстояние между Wikidata/ручной точкой и OSM.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import dataset

HERE = Path(__file__).resolve().parent
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
QUERY = """
[out:json][timeout:180];
(
  nwr["place"](42.45,44.65,44.15,46.75);
  nwr["historic"](42.45,44.65,44.15,46.75);
  nwr["tourism"="museum"](42.45,44.65,44.15,46.75);
  nwr["amenity"="place_of_worship"](42.45,44.65,44.15,46.75);
  nwr["natural"~"peak|water|cave_entrance"](42.45,44.65,44.15,46.75);
);
out center tags;
"""


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", value).strip()


def names(tags: dict) -> set[str]:
    values = []
    for key in ("name", "name:ru", "name:ce", "official_name", "old_name", "alt_name"):
        values.extend((tags.get(key) or "").split(";"))
    return {normalized(value) for value in values if normalized(value)}


def distance_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6_371_000
    lat1, lat2 = math.radians(a_lat), math.radians(b_lat)
    d_lat = lat2 - lat1
    d_lon = math.radians(b_lon - a_lon)
    hav = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))


def load_places() -> list[dict]:
    harvested = json.loads((HERE / "harvested_data.json").read_text(encoding="utf-8"))
    result = []
    for row in dataset.PLACES:
        if row.get("latitude") is None or row.get("longitude") is None:
            continue
        result.append({"place_slug": row["slug"], "name": row["name_ru"],
                       "alt_names": row.get("alt_names"), "latitude": row["latitude"],
                       "longitude": row["longitude"]})
    for row in harvested["places"]:
        if row.get("latitude") is None or row.get("longitude") is None:
            continue
        result.append({"place_external_id": row["external_id"], "name": row["name_ru"],
                       "alt_names": row.get("alt_names"), "latitude": row["latitude"],
                       "longitude": row["longitude"]})
    return result


def download() -> list[dict]:
    request = urllib.request.Request(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": QUERY}).encode(),
        headers={"User-Agent": "ChechnyaHistoryResearch/1.0"},
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)["elements"]


def osm_point(element: dict) -> tuple[float, float] | None:
    if "lat" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center:
        return center["lat"], center["lon"]
    return None


def harvest() -> list[dict]:
    by_name: dict[str, list[dict]] = {}
    for element in download():
        if not osm_point(element):
            continue
        for name in names(element.get("tags", {})):
            by_name.setdefault(name, []).append(element)

    evidence = []
    seen = set()
    for place in load_places():
        target_names = names({"name": place["name"], "alt_name": place.get("alt_names")})
        candidates = [item for name in target_names for item in by_name.get(name, [])]
        ranked = []
        for item in candidates:
            lat, lon = osm_point(item)
            ranked.append((distance_m(place["latitude"], place["longitude"], lat, lon), item, lat, lon))
        if not ranked:
            continue
        distance, item, lat, lon = min(ranked, key=lambda row: row[0])
        if distance > 10_000:
            continue
        external_id = f"{item['type']}/{item['id']}"
        owner = place.get("place_external_id") or place.get("place_slug")
        if (owner, external_id) in seen:
            continue
        seen.add((owner, external_id))
        row = {key: place[key] for key in ("place_external_id", "place_slug") if place.get(key)}
        row.update({
            "provider": "OpenStreetMap", "external_id": external_id,
            "latitude": lat, "longitude": lon, "distance_m": round(distance, 1),
            "source_url": f"https://www.openstreetmap.org/{external_id}",
            "match_method": "normalized_name_and_nearest_point",
            "verification_status": "corroborated" if distance <= 1_000 else "needs_review",
        })
        evidence.append(row)
    return evidence


if __name__ == "__main__":
    output = harvest()
    (HERE / "osm_evidence.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Сохранено независимых координатных свидетельств: {len(output)}")

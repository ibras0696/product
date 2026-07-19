#!/usr/bin/env python3
"""Harvest research candidates about Chechnya from Wikidata and Commons.

The generated JSON is intentionally moderation-only. Wikidata claims are useful for
discovery and deduplication, but are never promoted to ``verified`` automatically.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "harvested_data.json"
USER_AGENT = "history-chechnya-research/1.0 (moderation dataset)"
SPARQL_URL = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/"
QID_RE = re.compile(r"Q\d+$")
TAG_RE = re.compile(r"<[^>]+>")

DISTRICTS = {
    "Q482011": "achkhoy-martanovsky",
    "Q660676": "vedensky",
    "Q1027864": "groznensky",
    "Q657598": "gudermessky",
    "Q933085": "itum-kalinsky",
    "Q659105": "kurchaloevsky",
    "Q856368": "nadterechny",
    "Q1026766": "naursky",
    "Q1026761": "nozhay-yurtovsky",
    "Q856394": "sunzhensky",
    "Q1026606": "urus-martanovsky",
    "Q928616": "shalinsky",
    "Q933069": "sharoysky",
    "Q856410": "shatoysky",
    "Q1026803": "shelkovskoy",
}
DISTRICT_VALUES = " ".join(f"wd:{qid}" for qid in DISTRICTS)

SETTLEMENT_TYPES = {
    "Q515": "city",
    "Q532": "village",
    "Q771444": "village",
    "Q2023000": "village",
    "Q2514025": "town",
    "Q748331": "town",
    "Q7930989": "city",
    "Q106389302": "city",
    "Q1549591": "city",
    "Q486972": "locality",
}
OBJECT_TYPES = {
    "Q8502": "mountain",
    "Q4022": "river",
    "Q23397": "lake",
    "Q131681": "lake",
    "Q12518": "tower_complex",
    "Q32815": "mosque",
    "Q33506": "museum",
    "Q4989906": "memorial",
    "Q23413": "fortress",
    "Q1785071": "fortress",
    "Q811979": "locality",
    "Q39816": "locality",
    "Q46831": "mountain",
}
EVENT_TYPES = {
    "Q178561": "battle",
    "Q198": "war",
    "Q124734": "battle",
    "Q180684": "uprising",
    "Q188055": "battle",
    "Q8465": "war",
    "Q1190554": "battle",
    "Q350604": "battle",
    "Q13418847": "battle",
    "Q645883": "battle",
}


def _request_json(url: str, params: dict[str, str], attempts: int = 4) -> dict:
    encoded = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{encoded}", headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (TimeoutError, urllib.error.URLError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def _sparql(query: str) -> list[dict[str, str]]:
    payload = _request_json(SPARQL_URL, {"format": "json", "query": query})
    return [
        {key: value["value"] for key, value in row.items()}
        for row in payload["results"]["bindings"]
    ]


def _qid(value: str | None) -> str | None:
    if not value:
        return None
    match = QID_RE.search(value)
    return match.group() if match else None


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"([+-]?\d{1,6})-", value)
    return int(match.group(1)) if match else None


def _coordinate(value: str | None) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    match = re.fullmatch(r"Point\(([-.\d]+) ([-.\d]+)\)", value)
    if not match:
        return None, None
    return float(match.group(2)), float(match.group(1))


def _coordinate_quality(value: str | None) -> tuple[str, float | None]:
    if not value:
        return "unknown", None
    precision_m = float(value) * 111_320
    accuracy = "exact" if precision_m <= 25 else "approximate"
    return accuracy, round(precision_m, 2)


def _clean_html(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = html.unescape(TAG_RE.sub(" ", value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _merge_rows(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for row in rows:
        qid = _qid(row.get("item"))
        if not qid:
            continue
        target = merged.setdefault(qid, {})
        for key, value in row.items():
            target.setdefault(key, value)
    return merged


def _place_query(types: dict[str, str]) -> str:
    type_values = " ".join(f"wd:{qid}" for qid in types)
    return f"""
SELECT DISTINCT ?item ?label ?description ?type ?coord ?geoPrecision ?image ?district WHERE {{
  ?item wdt:P31 ?type; wdt:P131* wd:Q5187; rdfs:label ?label.
  VALUES ?type {{ {type_values} }}
  FILTER(LANG(?label) = "ru")
  OPTIONAL {{ ?item schema:description ?description. FILTER(LANG(?description) = "ru") }}
  OPTIONAL {{ ?item wdt:P625 ?coord }}
  OPTIONAL {{
    ?item p:P625/psv:P625 ?coordinateValue.
    ?coordinateValue wikibase:geoPrecision ?geoPrecision.
  }}
  OPTIONAL {{ ?item wdt:P18 ?image }}
  OPTIONAL {{ ?item wdt:P131+ ?district. VALUES ?district {{ {DISTRICT_VALUES} }} }}
}} ORDER BY ?label
"""


def harvest_places() -> list[dict]:
    result: dict[str, dict] = {}
    for type_map in (SETTLEMENT_TYPES, OBJECT_TYPES):
        for qid, row in _merge_rows(_sparql(_place_query(type_map))).items():
            latitude, longitude = _coordinate(row.get("coord"))
            accuracy, precision_m = _coordinate_quality(row.get("geoPrecision"))
            result[qid] = {
                "slug": f"wd-{qid.lower()}",
                "external_id": qid,
                "source_record_url": f"{WIKIDATA_ENTITY}{qid}",
                "name_ru": row["label"],
                "place_type": type_map.get(_qid(row.get("type")) or "", "locality"),
                "district": DISTRICTS.get(_qid(row.get("district")) or ""),
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_accuracy": accuracy,
                "coordinate_precision_m": precision_m,
                "coordinate_source_url": f"{WIKIDATA_ENTITY}{qid}",
                "description": row.get("description"),
                "verification_status": "needs_review",
                "source": "wikidata",
                "image": row.get("image"),
            }
    return sorted(result.values(), key=lambda row: (row["name_ru"], row["external_id"]))


def _person_category(description: str) -> str:
    lowered = description.casefold()
    rules = (
        (("военн", "генерал", "герой советского"), "military"),
        (("писател", "поэт", "актёр", "актер", "худож", "музыкант"), "cultural"),
        (("учёный", "ученый", "историк", "филолог", "врач"), "academic"),
        (("религи", "шейх", "имам", "богослов"), "religious"),
        (("полит", "государствен", "депутат", "президент"), "political"),
    )
    return next((category for words, category in rules if any(word in lowered for word in words)), "other")


def harvest_people() -> list[dict]:
    query = """
SELECT DISTINCT ?item ?label ?description ?birth ?death ?birthplace ?image WHERE {
  ?item wdt:P31 wd:Q5; wdt:P570 ?death; rdfs:label ?label.
  FILTER(LANG(?label) = "ru")
  { ?item wdt:P172 wd:Q31230 } UNION { ?item wdt:P19/wdt:P131* wd:Q5187 }
  OPTIONAL { ?item schema:description ?description. FILTER(LANG(?description) = "ru") }
  OPTIONAL { ?item wdt:P569 ?birth }
  OPTIONAL { ?item wdt:P19 ?birthplace }
  OPTIONAL { ?item wdt:P18 ?image }
} ORDER BY ?label
"""
    result = []
    for qid, row in _merge_rows(_sparql(query)).items():
        description = row.get("description") or "Историческая личность; сведения требуют проверки."
        result.append(
            {
                "slug": f"wd-{qid.lower()}",
                "external_id": qid,
                "source_record_url": f"{WIKIDATA_ENTITY}{qid}",
                "full_name_ru": row["label"],
                "birth_year": _year(row.get("birth")),
                "death_year": _year(row.get("death")),
                "birthplace_external_id": _qid(row.get("birthplace")),
                "title": description,
                "category": _person_category(description),
                "biography": description,
                "verification_status": "needs_review",
                "source": "wikidata",
                "image": row.get("image"),
            }
        )
    return sorted(result, key=lambda row: (row["full_name_ru"], row["external_id"]))


def harvest_events() -> list[dict]:
    type_values = " ".join(f"wd:{qid}" for qid in EVENT_TYPES)
    query = f"""
SELECT DISTINCT ?item ?label ?description ?type ?date ?start ?end ?place ?image WHERE {{
  ?item wdt:P31 ?type; wdt:P276/wdt:P131* wd:Q5187; rdfs:label ?label.
  VALUES ?type {{ {type_values} }} FILTER(LANG(?label) = "ru")
  OPTIONAL {{ ?item schema:description ?description. FILTER(LANG(?description) = "ru") }}
  OPTIONAL {{ ?item wdt:P585 ?date }} OPTIONAL {{ ?item wdt:P580 ?start }}
  OPTIONAL {{ ?item wdt:P582 ?end }} OPTIONAL {{ ?item wdt:P276 ?place }}
  OPTIONAL {{ ?item wdt:P18 ?image }}
}} ORDER BY ?label
"""
    result = []
    for qid, row in _merge_rows(_sparql(query)).items():
        start = _year(row.get("start") or row.get("date"))
        end = _year(row.get("end") or row.get("date"))
        result.append(
            {
                "slug": f"wd-{qid.lower()}",
                "external_id": qid,
                "source_record_url": f"{WIKIDATA_ENTITY}{qid}",
                "name_ru": row["label"],
                "event_type": EVENT_TYPES.get(_qid(row.get("type")) or "", "other"),
                "start_year": start,
                "end_year": end,
                "place_external_id": _qid(row.get("place")),
                "description": row.get("description") or "Историческое событие; сведения требуют проверки.",
                "verification_status": "needs_review",
                "source": "wikidata",
                "image": row.get("image"),
            }
        )
    return sorted(result, key=lambda row: (row["name_ru"], row["external_id"]))


def harvest_person_events() -> list[dict]:
    type_values = " ".join(f"wd:{qid}" for qid in EVENT_TYPES)
    query = f"""
SELECT DISTINCT ?person ?event WHERE {{
  ?person wdt:P31 wd:Q5; wdt:P570 ?death.
  {{ ?person wdt:P172 wd:Q31230 }} UNION {{ ?person wdt:P19/wdt:P131* wd:Q5187 }}
  ?event wdt:P31 ?type; wdt:P276/wdt:P131* wd:Q5187.
  VALUES ?type {{ {type_values} }}
  {{ ?person wdt:P1344 ?event }} UNION {{ ?event wdt:P710 ?person }}
}}
"""
    return [
        {
            "person_external_id": _qid(row.get("person")),
            "event_external_id": _qid(row.get("event")),
            "role": "Участие указано в Wikidata; роль требует проверки.",
            "verification_status": "needs_review",
            "source": "wikidata",
        }
        for row in _sparql(query)
        if _qid(row.get("person")) and _qid(row.get("event"))
    ]


def _commons_title(image_url: str) -> str:
    marker = "/Special:FilePath/"
    return "File:" + urllib.parse.unquote(image_url.split(marker, 1)[1]).replace("_", " ")


def harvest_media(owners: Iterable[tuple[str, dict]]) -> list[dict]:
    indexed = [(kind, row, _commons_title(row["image"])) for kind, row in owners if row.get("image")]
    metadata: dict[str, dict] = {}
    titles = sorted({title for _, _, title in indexed})
    for offset in range(0, len(titles), 50):
        payload = _request_json(
            COMMONS_API,
            {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "titles": "|".join(titles[offset : offset + 50]),
            },
        )
        for page in payload["query"]["pages"].values():
            if page.get("imageinfo"):
                metadata[page["title"]] = page["imageinfo"][0]
    media = []
    for kind, owner, title in indexed:
        info = metadata.get(title)
        if not info:
            continue
        meta = info.get("extmetadata", {})
        value = lambda key: meta.get(key, {}).get("value")
        media.append(
            {
                "owner_type": kind,
                "owner_external_id": owner["external_id"],
                "commons_title": title,
                "file_page_url": info["descriptionurl"],
                "original_url": info["url"],
                "artist": _clean_html(value("Artist")),
                "credit": _clean_html(value("Credit")),
                "license": value("LicenseShortName") or value("License"),
                "license_url": value("LicenseUrl"),
                "verification_status": "needs_review",
                "source": "wikimedia_commons",
            }
        )
    return media


def build_payload() -> dict:
    places = harvest_places()
    people = harvest_people()
    events = harvest_events()
    person_events = harvest_person_events()
    owners = [("place", row) for row in places]
    owners += [("person", row) for row in people]
    owners += [("event", row) for row in events]
    media = harvest_media(owners)
    for row in (*places, *people, *events):
        row.pop("image", None)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "policy": "Research candidates only; manual source review required before publication.",
        "sources": [
            {
                "slug": "rosstat_municipalities",
                "title": "Перечень муниципальных образований Чеченской Республики",
                "publisher": "Территориальный орган Росстата по Чеченской Республике",
                "url": "https://95.rosstat.gov.ru/folder/208692",
                "source_type": "official",
                "reliability": "high",
                "notes": "Официальный источник для проверки районов и муниципальных образований.",
            },
            {
                "slug": "wikidata",
                "title": "Wikidata: структурированные исследовательские кандидаты по Чечне",
                "publisher": "Wikimedia Foundation community",
                "url": "https://www.wikidata.org/wiki/Wikidata:Main_Page",
                "source_type": "dataset",
                "reliability": "medium",
                "notes": "Массовый discovery-источник; каждое утверждение проверяется по ссылкам элемента.",
            },
            {
                "slug": "wikimedia_commons",
                "title": "Wikimedia Commons: изображения и лицензионные метаданные",
                "publisher": "Wikimedia Foundation community",
                "url": "https://commons.wikimedia.org/",
                "source_type": "media_repository",
                "reliability": "medium",
                "notes": "Перед публикацией проверить изображённый объект, автора и актуальную лицензию.",
            },
        ],
        "places": places,
        "people": people,
        "events": events,
        "person_events": person_events,
        "media_assets": media,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Собрать research-кандидаты из Wikidata")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_payload()
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "Собрано:",
        len(payload["places"]), "мест;",
        len(payload["people"]), "персон;",
        len(payload["events"]), "событий;",
        len(payload["person_events"]), "связей персона-событие;",
        len(payload["media_assets"]), "медиа.",
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Собирает SQLite-БД истории Чечни из schema.sql и dataset.py.

Запуск:
    python3 docs/test/build_db.py            # создаёт docs/test/sqlite.db
    python3 docs/test/build_db.py --db /tmp/other.db

Скрипт идемпотентен: schema.sql пересоздаёт таблицы, поэтому повторный запуск
даёт тот же результат. Связи в dataset.py заданы текстовыми slug'ами и
резолвятся здесь в целочисленные внешние ключи. Отсутствие slug'а — ошибка сборки.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataset  # noqa: E402  (локальный модуль рядом со скриптом)
import deep_research  # noqa: E402

SCHEMA_PATH = HERE / "schema.sql"
DEFAULT_DB = HERE / "sqlite.db"
HARVEST_PATH = HERE / "harvested_data.json"
OSM_EVIDENCE_PATH = HERE / "osm_evidence.json"
ADDITIONAL_MEDIA_PATH = HERE / "additional_media.json"

PLACE_EXTERNAL_MATCHES = {
    "Q652052": "argun-river",
    "Q4068870": "argun-gorge",
    "Q1739762": "kezenoy-am",
    "Q768463": "tebulosmta",
    "Q340549": "heart-of-chechnya",
    "Q75043630": "pride-of-muslims",
    "Q4319643": "nikaroy",
    "Q4498895": "khoy",
    "Q16679941": "national-museum",
}
PEOPLE_EXTERNAL_MATCHES = {
    "Q1849933": "sheikh-mansur",
    "Q22074736": "beybulat-taimiev",
    "Q4075730": "baysangur",
    "Q22919503": "uma-duev",
    "Q4153106": "zelimkhan",
    "Q4523148": "sheripov-aslanbek",
    "Q4112141": "visaitov",
    "Q4197965": "idrisov",
    "Q16447989": "magomed-mirzoev",
    "Q4155413": "dachiev",
    "Q21857063": "mazaev",
    "Q15065191": "gazimagomadov",
    "Q4453077": "tashukhadzhiev",
    "Q2996084": "esambaev",
}
EVENT_EXTERNAL_MATCHES = {
    "Q4872462": "battle-aldy-1785",
    "Q4438368": "battle-valerik-1840",
}


def _require(mapping: dict[str, int], slug: str | None, table: str) -> int | None:
    """Вернуть id по slug; None пропускается, неизвестный slug — ошибка."""
    if slug is None:
        return None
    if slug not in mapping:
        raise KeyError(f"Неизвестный slug '{slug}' для таблицы {table}")
    return mapping[slug]


def _insert(cur: sqlite3.Cursor, table: str, row: dict) -> int:
    columns = ", ".join(row)
    placeholders = ", ".join(f":{c}" for c in row)
    cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", row)
    return int(cur.lastrowid)


def _insert_or_ignore(cur: sqlite3.Cursor, table: str, row: dict) -> None:
    columns = ", ".join(row)
    placeholders = ", ".join(f":{column}" for column in row)
    cur.execute(f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})", row)


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", value).strip()


def _harvested() -> dict:
    if not HARVEST_PATH.exists():
        return {
            "sources": [], "places": [], "people": [], "events": [],
            "person_events": [], "media_assets": [],
        }
    return json.loads(HARVEST_PATH.read_text(encoding="utf-8"))


def _osm_evidence() -> list[dict]:
    if not OSM_EVIDENCE_PATH.exists():
        return []
    return json.loads(OSM_EVIDENCE_PATH.read_text(encoding="utf-8"))


def _additional_media() -> list[dict]:
    if not ADDITIONAL_MEDIA_PATH.exists():
        return []
    return json.loads(ADDITIONAL_MEDIA_PATH.read_text(encoding="utf-8"))


def _unique_name_ids(rows: list[dict], name_key: str, ids: dict[str, int]) -> dict[str, int]:
    candidates: dict[str, list[int]] = {}
    for row in rows:
        candidates.setdefault(_normalized(row[name_key]), []).append(ids[row["slug"]])
    return {name: values[0] for name, values in candidates.items() if len(values) == 1}


def _base_coordinate_fields(data: dict, source_urls: dict[str, str | None]) -> None:
    data["source_record_url"] = source_urls.get(data.get("source"))
    if data.get("latitude") is None or data.get("longitude") is None:
        data["coordinate_accuracy"] = "unknown"
        return
    data["coordinate_accuracy"] = "approximate"
    data["coordinate_source_url"] = source_urls.get(data.get("source"))


def build(db_path: Path) -> dict[str, int]:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    harvested = _harvested()

    src_ids: dict[str, int] = {}
    all_sources = [*dataset.SOURCES, *harvested["sources"], *deep_research.SOURCES]
    for row in all_sources:
        if row["slug"] in src_ids:
            raise ValueError(f"Дублирующийся источник: {row['slug']}")
        src_ids[row["slug"]] = _insert(cur, "sources", dict(row))
    source_urls = {row["slug"]: row.get("url") for row in all_sources}

    district_ids: dict[str, int] = {}
    for row in dataset.DISTRICTS:
        data = dict(row)
        data["verification_status"] = "corroborated"
        data["source_id"] = src_ids["rosstat_municipalities"]
        district_ids[row["slug"]] = _insert(cur, "districts", data)

    place_ids: dict[str, int] = {}
    place_external_ids: dict[str, int] = {}
    for row in dataset.PLACES:
        data = dict(row)
        _base_coordinate_fields(data, source_urls)
        data["district_id"] = _require(district_ids, data.pop("district", None), "places")
        data["source_id"] = _require(src_ids, data.pop("source", None), "places")
        place_ids[data["slug"]] = _insert(cur, "places", data)
    place_names = _unique_name_ids(dataset.PLACES, "name_ru", place_ids)
    for row in harvested["places"]:
        data = dict(row)
        external_id = data["external_id"]
        matched_slug = PLACE_EXTERNAL_MATCHES.get(external_id)
        matched_id = place_ids.get(matched_slug) if matched_slug else place_names.get(
            _normalized(data["name_ru"])
        )
        if matched_id:
            cur.execute(
                "UPDATE places SET external_id = COALESCE(external_id, ?) WHERE id = ?",
                (external_id, matched_id),
            )
            place_external_ids[external_id] = matched_id
            continue
        data["district_id"] = _require(district_ids, data.pop("district", None), "places")
        data["source_id"] = _require(src_ids, data.pop("source", None), "places")
        place_id = _insert(cur, "places", data)
        place_ids[data["slug"]] = place_id
        place_external_ids[external_id] = place_id

    people_ids: dict[str, int] = {}
    people_external_ids: dict[str, int] = {}
    for row in dataset.PEOPLE:
        data = dict(row)
        data["source_record_url"] = source_urls.get(data.get("source"))
        data["birthplace_id"] = _require(place_ids, data.pop("birthplace", None), "people")
        data["source_id"] = _require(src_ids, data.pop("source", None), "people")
        people_ids[data["slug"]] = _insert(cur, "people", data)
    people_names = _unique_name_ids(dataset.PEOPLE, "full_name_ru", people_ids)
    for row in harvested["people"]:
        data = dict(row)
        if (data.get("birth_year") is not None and data.get("death_year") is not None
                and data["birth_year"] > data["death_year"]):
            bad_year = data["birth_year"]
            data["birth_year"] = None
            note = f"Wikidata содержит невозможный год рождения {bad_year}; значение исключено."
            data["biography"] = f"{data.get('biography') or ''} {note}".strip()
        external_id = data["external_id"]
        matched_slug = PEOPLE_EXTERNAL_MATCHES.get(external_id)
        matched_id = people_ids.get(matched_slug) if matched_slug else people_names.get(
            _normalized(data["full_name_ru"])
        )
        if matched_id:
            cur.execute(
                "UPDATE people SET external_id = COALESCE(external_id, ?) WHERE id = ?",
                (external_id, matched_id),
            )
            people_external_ids[external_id] = matched_id
            continue
        birthplace_external_id = data.pop("birthplace_external_id", None)
        data["birthplace_id"] = place_external_ids.get(birthplace_external_id)
        data["source_id"] = _require(src_ids, data.pop("source", None), "people")
        person_id = _insert(cur, "people", data)
        people_ids[data["slug"]] = person_id
        people_external_ids[external_id] = person_id

    event_ids: dict[str, int] = {}
    event_external_ids: dict[str, int] = {}
    for row in dataset.EVENTS:
        data = dict(row)
        data["source_record_url"] = source_urls.get(data.get("source"))
        data["place_id"] = _require(place_ids, data.pop("place", None), "events")
        data["source_id"] = _require(src_ids, data.pop("source", None), "events")
        event_ids[data["slug"]] = _insert(cur, "events", data)
    event_names = _unique_name_ids(dataset.EVENTS, "name_ru", event_ids)
    for row in harvested["events"]:
        data = dict(row)
        external_id = data["external_id"]
        matched_slug = EVENT_EXTERNAL_MATCHES.get(external_id)
        matched_id = event_ids.get(matched_slug) if matched_slug else event_names.get(
            _normalized(data["name_ru"])
        )
        if matched_id:
            cur.execute(
                "UPDATE events SET external_id = COALESCE(external_id, ?) WHERE id = ?",
                (external_id, matched_id),
            )
            event_external_ids[external_id] = matched_id
            continue
        place_external_id = data.pop("place_external_id", None)
        data["place_id"] = place_external_ids.get(place_external_id)
        data["source_id"] = _require(src_ids, data.pop("source", None), "events")
        event_id = _insert(cur, "events", data)
        event_ids[data["slug"]] = event_id
        event_external_ids[external_id] = event_id

    for row in dataset.DEEDS:
        data = dict(row)
        data["person_id"] = _require(people_ids, data.pop("person"), "deeds")
        data["event_id"] = _require(event_ids, data.pop("event", None), "deeds")
        data["place_id"] = _require(place_ids, data.pop("place", None), "deeds")
        data["source_id"] = _require(src_ids, data.pop("source", None), "deeds")
        _insert(cur, "deeds", data)

    for row in dataset.RESIDENCES:
        data = dict(row)
        data["person_id"] = _require(people_ids, data.pop("person"), "residences")
        data["place_id"] = _require(place_ids, data.pop("place"), "residences")
        person_row = next(item for item in dataset.PEOPLE if item["slug"] == row["person"])
        data["source_id"] = _require(src_ids, person_row.get("source"), "residences")
        data["verification_status"] = person_row["verification_status"]
        _insert(cur, "residences", data)

    for row in harvested["people"]:
        person_id = people_external_ids.get(row["external_id"])
        place_id = place_external_ids.get(row.get("birthplace_external_id"))
        if not person_id or not place_id:
            continue
        cur.execute(
            """INSERT OR IGNORE INTO residences
               (person_id, place_id, relation, notes, verification_status, source_id)
               VALUES (?, ?, 'born', ?, 'needs_review', ?)""",
            (person_id, place_id, "Связь массово извлечена из Wikidata.", src_ids["wikidata"]),
        )

    for row in dataset.PERSON_EVENTS:
        data = dict(row)
        data["person_id"] = _require(people_ids, data.pop("person"), "person_events")
        data["event_id"] = _require(event_ids, data.pop("event"), "person_events")
        event_row = next(item for item in dataset.EVENTS if item["slug"] == row["event"])
        data["source_id"] = _require(src_ids, event_row.get("source"), "person_events")
        data["verification_status"] = event_row["verification_status"]
        _insert(cur, "person_events", data)

    for row in harvested.get("person_events", []):
        person_id = people_external_ids.get(row["person_external_id"])
        event_id = event_external_ids.get(row["event_external_id"])
        if not person_id or not event_id:
            continue
        cur.execute(
            """INSERT OR IGNORE INTO person_events
               (person_id, event_id, role, verification_status, source_id)
               VALUES (?, ?, ?, ?, ?)""",
            (
                person_id,
                event_id,
                row.get("role"),
                row["verification_status"],
                src_ids[row["source"]],
            ),
        )

    for row in [*harvested["media_assets"], *_additional_media()]:
        data = dict(row)
        owner_type = data.pop("owner_type")
        owner_external_id = data.pop("owner_external_id")
        owner_maps = {
            "place": ("place_id", place_external_ids),
            "person": ("person_id", people_external_ids),
            "event": ("event_id", event_external_ids),
        }
        owner_column, owner_ids = owner_maps[owner_type]
        owner_id = owner_ids.get(owner_external_id)
        if not owner_id:
            continue
        data[owner_column] = owner_id
        data["source_id"] = _require(src_ids, data.pop("source"), "media_assets")
        _insert(cur, "media_assets", data)

    for row in _osm_evidence():
        place_id = place_external_ids.get(row.get("place_external_id"))
        if not place_id:
            place_id = place_ids.get(row.get("place_slug"))
        if not place_id:
            continue
        data = dict(row)
        data.pop("place_external_id", None)
        data.pop("place_slug", None)
        data["place_id"] = place_id
        _insert_or_ignore(cur, "coordinate_evidence", data)

    document_ids: dict[str, int] = {}
    for row in deep_research.DOCUMENTS:
        data = dict(row)
        data["source_id"] = _require(src_ids, data.pop("source"), "source_documents")
        document_ids[data["slug"]] = _insert(cur, "source_documents", data)

    owner_maps = {
        "place": ("place_id", place_ids),
        "person": ("person_id", people_ids),
        "event": ("event_id", event_ids),
    }
    for owner_type, owner_slug, document_slug, claim, status in deep_research.CITATIONS:
        owner_column, owner_ids = owner_maps[owner_type]
        _insert(cur, "fact_citations", {
            owner_column: _require(owner_ids, owner_slug, "fact_citations"),
            "document_id": _require(document_ids, document_slug, "fact_citations"),
            "claim_summary": claim,
            "verification_status": status,
        })

    conn.commit()

    tables = [
        "sources", "districts", "places", "people",
        "events", "deeds", "residences", "person_events", "media_assets",
        "coordinate_evidence", "source_documents", "fact_citations",
    ]
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}

    # Проверка целостности внешних ключей.
    violations = cur.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        conn.close()
        raise RuntimeError(f"Нарушения внешних ключей: {violations}")

    conn.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка БД истории Чечни")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="путь к .db файлу")
    args = parser.parse_args()

    counts = build(args.db)
    total = sum(counts.values())
    print(f"БД собрана: {args.db}")
    for table, count in counts.items():
        print(f"  {table:<14} {count:>4}")
    print(f"  {'ИТОГО':<14} {total:>4} строк")


if __name__ == "__main__":
    main()

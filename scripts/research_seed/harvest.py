from types import ModuleType

from research_seed.common import (
    PLACE_TYPES,
    Payload,
    compact,
    empty_payload,
    entity_record,
    name_records,
    review_note,
    source_link,
    source_record,
    stable_id,
    text_record,
)
from research_seed.manual import (
    RelationSpec,
    add_manual_entities,
    add_manual_relations,
    append_relation,
)


def _external_ids(
    dataset: ModuleType, harvest: dict[str, object], mappings: ModuleType
) -> dict[tuple[str, str], str]:
    manual = {
        "place": {row["slug"]: stable_id("entity", "place", row["slug"]) for row in dataset.PLACES},
        "person": {
            row["slug"]: stable_id("entity", "person", row["slug"]) for row in dataset.PEOPLE
        },
        "event": {row["slug"]: stable_id("entity", "event", row["slug"]) for row in dataset.EVENTS},
    }
    reviewed = {
        "place": mappings.PLACE_EXTERNAL_MATCHES,
        "person": mappings.PEOPLE_EXTERNAL_MATCHES,
        "event": mappings.EVENT_EXTERNAL_MATCHES,
    }
    candidates = {
        "place": harvest["places"],
        "person": harvest["people"],
        "event": harvest["events"],
    }
    result = {}
    for kind, rows in candidates.items():
        for row in rows:
            qid = row["external_id"]
            matched_slug = reviewed[kind].get(qid)
            result[(kind, qid)] = (
                manual[kind][matched_slug]
                if matched_slug
                else stable_id("entity", kind, "qid", qid)
            )
    return result


def _provenance(row: dict[str, object]) -> str:
    return compact(
        f"Внешний идентификатор Wikidata: {row['external_id']}.",
        f"URL записи источника: {row.get('source_record_url')}.",
        (
            f"Источник координат: {row.get('coordinate_source_url')}. "
            f"Точность: {row.get('coordinate_accuracy')}; "
            f"заявленная точность, м: {row.get('coordinate_precision_m')}."
            if "coordinate_accuracy" in row
            else None
        ),
        review_note(row),
    )


def _add_entities(
    payload: Payload,
    harvest: dict[str, object],
    mappings: ModuleType,
    ids: dict[tuple[str, str], str],
) -> None:
    reviewed = {
        "place": mappings.PLACE_EXTERNAL_MATCHES,
        "person": mappings.PEOPLE_EXTERNAL_MATCHES,
        "event": mappings.EVENT_EXTERNAL_MATCHES,
    }
    configurations = (
        ("place", harvest["places"], "name_ru", "description"),
        ("person", harvest["people"], "full_name_ru", "biography"),
        ("event", harvest["events"], "name_ru", "description"),
    )
    for kind, rows, title_key, description_key in configurations:
        for row in rows:
            qid = row["external_id"]
            if qid in reviewed[kind]:
                continue
            entity_type = PLACE_TYPES[row["place_type"]] if kind == "place" else kind
            entity = entity_record(kind, row, entity_type, external=True)
            entity_id = ids[(kind, qid)]
            text = row.get(description_key) or row.get("title") or "Исследовательский кандидат"
            payload["entities"].append(entity)
            payload["entity_texts"].append(
                text_record(entity_id, row[title_key], text, compact(text, _provenance(row)))
            )
            payload["entity_names"].extend(name_records(entity_id, row[title_key]))
            payload["entity_sources"].append(source_link(entity_id, row["source"]))


def _add_relations(
    payload: Payload, harvest: dict[str, object], ids: dict[tuple[str, str], str]
) -> None:
    seen = {
        (row["source_entity_id"], row["target_entity_id"], row["type"])
        for row in payload["relations"]
    }

    def add(
        key: str,
        endpoints: tuple[str | None, str | None],
        classification: tuple[str, str],
        description: str,
    ) -> None:
        source_id, target_id = endpoints
        relation_type, title = classification
        identity = (source_id, target_id, relation_type)
        if source_id is None or target_id is None or source_id == target_id or identity in seen:
            return
        seen.add(identity)
        append_relation(
            payload,
            RelationSpec(
                key=key,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                title=title,
                description=compact(description, "Статус исследования: needs_review."),
                source_slug="wikidata",
            ),
        )

    for row in harvest["people"]:
        person_qid, place_qid = row["external_id"], row.get("birthplace_external_id")
        add(
            f"wikidata-birth:{person_qid}:{place_qid}",
            (ids.get(("person", person_qid)), ids.get(("place", place_qid))),
            ("born_in", "Место рождения"),
            f"Wikidata: {person_qid} → {place_qid}.",
        )
    for row in harvest["events"]:
        event_qid, place_qid = row["external_id"], row.get("place_external_id")
        add(
            f"wikidata-event-place:{event_qid}:{place_qid}",
            (ids.get(("event", event_qid)), ids.get(("place", place_qid))),
            ("located_in", "Место события"),
            f"Wikidata: {event_qid} → {place_qid}.",
        )
    for row in harvest["person_events"]:
        person_qid, event_qid = row["person_external_id"], row["event_external_id"]
        add(
            f"wikidata-person-event:{person_qid}:{event_qid}",
            (ids.get(("person", person_qid)), ids.get(("event", event_qid))),
            ("participated_in", "Участие в событии"),
            compact(row.get("role"), f"Wikidata: {person_qid} → {event_qid}."),
        )


def _add_commons(
    payload: Payload, harvest: dict[str, object], ids: dict[tuple[str, str], str]
) -> None:
    for row in harvest["media_assets"]:
        entity_id = ids.get((row["owner_type"], row["owner_external_id"]))
        if entity_id is None:
            raise ValueError(f"unresolved Commons owner {row['owner_external_id']}")
        source_id = stable_id(
            "source",
            "commons",
            row["owner_type"],
            row["owner_external_id"],
            row["file_page_url"],
        )
        artist = str(row.get("artist") or "").strip()
        original_url = str(row["original_url"])
        payload["sources"].append(
            {
                "id": source_id,
                "title": str(row["commons_title"])[:500],
                "type": "photo",
                "author": artist[:300] or None,
                "publisher": "Wikimedia Commons",
                "publication_year": None,
                "url": row["file_page_url"],
                "archive_reference": original_url if len(original_url) <= 500 else None,
                "description": compact(
                    f"Страница файла: {row['file_page_url']}",
                    f"Оригинал: {row['original_url']}",
                    f"Автор: {row.get('artist') or 'не указан'}",
                    f"Credit: {row.get('credit') or 'не указан'}",
                    f"Лицензия: {row.get('license') or 'не указана'}",
                    f"URL лицензии: {row.get('license_url') or 'не указан'}",
                    review_note(row),
                ),
                "is_verified": False,
                "status": "draft",
            }
        )
        payload["entity_sources"].append(
            {
                "id": stable_id("entity-source", entity_id, source_id),
                "entity_id": entity_id,
                "source_id": source_id,
            }
        )


def build_payload(dataset: ModuleType, harvest: dict[str, object], mappings: ModuleType) -> Payload:
    payload = empty_payload()
    payload["districts"] = [
        {
            "id": stable_id("district", row["slug"]),
            "slug": row["slug"],
            "title_ru": row["name_ru"],
            "title_ce": row.get("name_ce"),
        }
        for row in dataset.DISTRICTS
    ]
    payload["sources"] = [source_record(row) for row in [*dataset.SOURCES, *harvest["sources"]]]
    add_manual_entities(payload, dataset)
    add_manual_relations(payload, dataset)
    ids = _external_ids(dataset, harvest, mappings)
    _add_entities(payload, harvest, mappings, ids)
    _add_relations(payload, harvest, ids)
    _add_commons(payload, harvest, ids)
    for records in payload.values():
        records.sort(key=lambda record: str(record["id"]))
    return payload


def build_demo_payload(
    dataset: ModuleType, harvest: dict[str, object], mappings: ModuleType
) -> Payload:
    payload = build_payload(dataset, harvest, mappings)
    for record in payload["sources"]:
        record["status"] = "published"
        record["is_verified"] = True
    for group in ("entities", "relations"):
        for record in payload[group]:
            record["status"] = "published"
    return payload

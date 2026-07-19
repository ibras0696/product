from dataclasses import dataclass
from types import ModuleType

from research_seed.common import (
    PLACE_TYPES,
    RESIDENCE_TYPES,
    Payload,
    compact,
    entity_record,
    name_records,
    review_note,
    source_link,
    stable_id,
    text_record,
)


@dataclass(frozen=True, slots=True)
class EntitySpec:
    kind: str
    row: dict[str, object]
    entity_type: str
    title: object
    short: object
    full: object
    district_id: str | None = None
    ce_title: object = None


def _append_entity(
    payload: Payload,
    spec: EntitySpec,
) -> None:
    entity = entity_record(spec.kind, spec.row, spec.entity_type, spec.district_id)
    entity_id = str(entity["id"])
    payload["entities"].append(entity)
    payload["entity_texts"].append(text_record(entity_id, spec.title, spec.short, spec.full))
    payload["entity_names"].extend(
        name_records(entity_id, spec.title, spec.row.get("alt_names"), spec.ce_title)
    )
    if source_slug := spec.row.get("source"):
        payload["entity_sources"].append(source_link(entity_id, str(source_slug)))


def add_manual_entities(payload: Payload, dataset: ModuleType) -> None:
    places = {row["slug"]: row for row in dataset.PLACES}
    for row in dataset.PLACES:
        district_id = stable_id("district", row["district"]) if row.get("district") else None
        full = compact(
            row.get("description"),
            row.get("historical_significance"),
            row.get("founded"),
            review_note(row),
        )
        _append_entity(
            payload,
            EntitySpec(
                "place",
                row,
                PLACE_TYPES[row["place_type"]],
                row["name_ru"],
                row["description"],
                full,
                district_id,
                row.get("name_ce"),
            ),
        )
    for row in dataset.PEOPLE:
        deeds = [
            compact(item["title"], item["description"], item.get("award"), review_note(item))
            for item in dataset.DEEDS
            if item["person"] == row["slug"] and not (item.get("event") or item.get("place"))
        ]
        _append_entity(
            payload,
            EntitySpec(
                "person",
                row,
                "person",
                row["full_name_ru"],
                row.get("title") or row.get("occupation") or "Историческая личность",
                compact(row["biography"], review_note(row), *deeds),
                ce_title=row.get("full_name_ce"),
            ),
        )
    for row in dataset.EVENTS:
        place = places.get(row.get("place"))
        district = place.get("district") if place else None
        _append_entity(
            payload,
            EntitySpec(
                "event",
                row,
                "event",
                row["name_ru"],
                row["description"],
                compact(row.get("date_text"), row["description"], review_note(row)),
                stable_id("district", district) if district else None,
            ),
        )


@dataclass(frozen=True, slots=True)
class RelationSpec:
    key: str
    source_id: str
    target_id: str
    relation_type: str
    title: str
    description: str
    source_slug: str
    period_from: object = None
    period_to: object = None


def append_relation(
    payload: Payload,
    spec: RelationSpec,
) -> None:
    relation_id = stable_id("relation", spec.key)
    payload["relations"].append(
        {
            "id": relation_id,
            "source_entity_id": spec.source_id,
            "target_entity_id": spec.target_id,
            "type": spec.relation_type,
            "title_ru": spec.title,
            "title_ce": None,
            "description_ru": spec.description,
            "description_ce": None,
            "period_from": spec.period_from,
            "period_to": spec.period_to,
            "status": "draft",
        }
    )
    source_record_id = stable_id("source", spec.source_slug)
    payload["relation_sources"].append(
        {
            "id": stable_id("relation-source", relation_id, source_record_id),
            "relation_id": relation_id,
            "source_id": source_record_id,
        }
    )


def add_manual_relations(payload: Payload, dataset: ModuleType) -> None:
    people_sources = {row["slug"]: row["source"] for row in dataset.PEOPLE}
    for index, row in enumerate(dataset.RESIDENCES):
        relation_type, title = RESIDENCE_TYPES[row["relation"]]
        append_relation(
            payload,
            RelationSpec(
                key=f"residence:{row['person']}:{row['place']}:{index}",
                source_id=stable_id("entity", "person", row["person"]),
                target_id=stable_id("entity", "place", row["place"]),
                relation_type=relation_type,
                title=title,
                description=compact(row.get("notes"), row.get("period"), title),
                source_slug=people_sources[row["person"]],
                period_from=int(row["period"]) if row.get("period") else None,
            ),
        )
    for index, row in enumerate(dataset.PERSON_EVENTS):
        append_relation(
            payload,
            RelationSpec(
                key=f"person-event:{row['person']}:{row['event']}:{index}",
                source_id=stable_id("entity", "person", row["person"]),
                target_id=stable_id("entity", "event", row["event"]),
                relation_type="participated_in",
                title="Участие в событии",
                description=row["role"],
                source_slug=people_sources[row["person"]],
            ),
        )
    for row in dataset.EVENTS:
        if place := row.get("place"):
            append_relation(
                payload,
                RelationSpec(
                    key=f"event-place:{row['slug']}",
                    source_id=stable_id("entity", "event", row["slug"]),
                    target_id=stable_id("entity", "place", place),
                    relation_type="located_in",
                    title="Место события",
                    description=row["description"],
                    source_slug=row["source"],
                    period_from=row.get("start_year"),
                    period_to=row.get("end_year"),
                ),
            )
    for index, row in enumerate(dataset.DEEDS):
        target_kind = "event" if row.get("event") else "place"
        if target_slug := row.get("event") or row.get("place"):
            append_relation(
                payload,
                RelationSpec(
                    key=f"deed:{row['person']}:{index}",
                    source_id=stable_id("entity", "person", row["person"]),
                    target_id=stable_id("entity", target_kind, target_slug),
                    relation_type=(
                        "participated_in" if target_kind == "event" else "connected_with"
                    ),
                    title=row["title"],
                    description=compact(
                        row["description"], row.get("award"), row.get("award_date")
                    ),
                    source_slug=row["source"],
                    period_from=row.get("year"),
                ),
            )

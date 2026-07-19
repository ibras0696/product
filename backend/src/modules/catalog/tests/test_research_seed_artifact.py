from collections import Counter
from pathlib import Path
from uuid import UUID, uuid5

from modules.catalog.seed import (
    MAX_SEED_BYTES,
    MAX_SEED_RECORDS,
    SeedPayload,
    load_seed_batches,
)

SEED_ROOT = Path(__file__).resolve().parents[4] / "seeds"
RESEARCH_PATH = SEED_ROOT / "research_batches"
DEMO_PATH = SEED_ROOT / "research_demo_batches"
NAMESPACE = UUID("d608b8ce-99f7-4de6-9b9e-1f06036d9b19")
EXPECTED_COUNTS = {
    "districts": 15,
    "sources": 451,
    "entities": 1_339,
    "entity_texts": 1_339,
    "entity_names": 1_352,
    "relations": 494,
    "entity_sources": 1_776,
    "relation_sources": 494,
}


def _records(batches: tuple[SeedPayload, ...]) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for batch in batches:
        for group, items in batch.groups.items():
            for item in items:
                key = f"{group}:{item['id']}"
                assert key not in records or records[key] == item
                records[key] = dict(item)
    return records


def _by_group(records: dict[str, dict[str, object]]) -> Counter[str]:
    return Counter(key.partition(":")[0] for key in records)


def _group(records: dict[str, dict[str, object]], name: str) -> list[dict[str, object]]:
    return [value for key, value in records.items() if key.startswith(f"{name}:")]


def _assert_bounded_batches(batches: tuple[SeedPayload, ...]) -> None:
    for path, batch in zip(sorted(RESEARCH_PATH.glob("*.json")), batches, strict=True):
        assert path.stat().st_size <= MAX_SEED_BYTES
        assert batch.record_count <= MAX_SEED_RECORDS


def _assert_photo_provenance(photo: dict[str, object]) -> None:
    assert str(photo["url"]).startswith("https://commons.wikimedia.org/")
    original = photo["archive_reference"]
    assert original is None or str(original).startswith("https://upload.wikimedia.org/")
    description = str(photo["description"])
    assert "Оригинал: https://upload.wikimedia.org/" in description
    assert "Лицензия:" in description
    assert "URL лицензии:" in description
    assert "Статус исследования: needs_review." in description


def _assert_photo_field_bounds(photo: dict[str, object]) -> None:
    assert len(str(photo["title"])) <= 500
    assert len(str(photo["author"] or "")) <= 300
    assert len(str(photo["archive_reference"] or "")) <= 500


def _relation_identity(item: dict[str, object]) -> tuple[object, object, object]:
    return item["source_entity_id"], item["target_entity_id"], item["type"]


def test_research_batches_are_bounded_complete_and_draft_only() -> None:
    batches = load_seed_batches(RESEARCH_PATH)
    records = _records(batches)

    assert _by_group(records) == EXPECTED_COUNTS
    assert len(batches) == 9
    _assert_bounded_batches(batches)

    entities = _group(records, "entities")
    relations = _group(records, "relations")
    sources = _group(records, "sources")
    assert all(item["status"] == "draft" for item in entities + relations + sources)
    assert all(item["is_verified"] is False for item in sources)


def test_explicit_qid_mapping_keeps_manual_ids_and_rejects_name_only_merge() -> None:
    records = _records(load_seed_batches(RESEARCH_PATH))

    manual_avtury = str(uuid5(NAMESPACE, "entity:place:avtury"))
    harvested_same_name = str(uuid5(NAMESPACE, "entity:place:qid:Q791816"))
    explicit_argun_river = str(uuid5(NAMESPACE, "entity:place:argun-river"))
    unsafe_duplicate = str(uuid5(NAMESPACE, "entity:place:qid:Q652052"))

    assert f"entities:{manual_avtury}" in records
    assert f"entities:{harvested_same_name}" in records
    assert f"entities:{explicit_argun_river}" in records
    assert f"entities:{unsafe_duplicate}" not in records


def test_harvested_provenance_and_commons_rights_are_preserved() -> None:
    records = _records(load_seed_batches(RESEARCH_PATH))
    texts = _group(records, "entity_texts")
    candidate_texts = [
        item for item in texts if "Внешний идентификатор Wikidata:" in str(item["full_description"])
    ]
    sources = _group(records, "sources")
    photos = [item for item in sources if item["type"] == "photo"]
    assert len(candidate_texts) == 1_246
    assert all(
        "URL записи источника: https://www.wikidata.org/wiki/Q" in str(item["full_description"])
        for item in candidate_texts
    )
    assert len(photos) == 437
    for photo in photos:
        _assert_photo_provenance(photo)
        _assert_photo_field_bounds(photo)


def test_harvested_relation_graph_is_unique_and_has_no_self_edges() -> None:
    records = _records(load_seed_batches(RESEARCH_PATH))
    relations = _group(records, "relations")
    harvested_relations = [item for item in relations if "Wikidata:" in str(item["description_ru"])]
    identities = [_relation_identity(item) for item in harvested_relations]
    all_identities = Counter(_relation_identity(item) for item in relations)
    assert len(harvested_relations) == 443
    assert len(identities) == len(set(identities))
    assert all(all_identities[identity] == 1 for identity in identities)
    assert all(source != target for source, target, _ in identities)


def test_local_demo_publishes_same_catalog_records_with_review_markers() -> None:
    default = _records(load_seed_batches(RESEARCH_PATH))
    demo = _records(load_seed_batches(DEMO_PATH))

    assert default.keys() == demo.keys()
    for key, item in demo.items():
        if key.startswith(("entities:", "relations:", "sources:")):
            assert item["status"] == "published"
        if key.startswith("sources:"):
            assert item["is_verified"] is True
    assert all(
        "Статус исследования: needs_review." in str(item["description"])
        for key, item in demo.items()
        if key.startswith("sources:") and item["type"] == "photo"
    )

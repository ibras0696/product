import json
from pathlib import Path

from research_seed.common import (
    MAX_BATCH_BYTES,
    MAX_BATCH_RECORDS,
    Payload,
    empty_payload,
)

RecordItem = tuple[str, dict[str, object]]
NamedBatch = tuple[str, Payload]
LEGACY_SEED = Path(__file__).parents[2] / "backend" / "seeds" / "chechnya_research.json"
LEGACY_KEY_FIELDS = {
    "entity_texts": ("entity_id", "locale"),
    "entity_names": ("entity_id", "locale", "name"),
    "entity_sources": ("entity_id", "source_id"),
    "relation_sources": ("relation_id", "source_id"),
}


def preserve_legacy_record_ids(payload: Payload) -> Payload:
    """Keep stable child IDs already present in local demo installations."""
    legacy = json.loads(LEGACY_SEED.read_text(encoding="utf-8"))
    for group, fields in LEGACY_KEY_FIELDS.items():
        ids = {
            tuple(record[field] for field in fields): record["id"]
            for record in legacy[group]
        }
        for record in payload[group]:
            key = tuple(record[field] for field in fields)
            if legacy_id := ids.get(key):
                record["id"] = legacy_id
    return payload


def render_payload(payload: Payload) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _bundle_payload(records: list[RecordItem]) -> Payload:
    payload = empty_payload()
    seen: dict[tuple[str, object], dict[str, object]] = {}
    for group, record in records:
        key = (group, record["id"])
        if current := seen.get(key):
            if current != record:
                raise ValueError(f"conflicting generated record {group}:{record['id']}")
            continue
        seen[key] = record
        payload[group].append(record)
    return payload


def _exceeds_bounds(payload: Payload) -> bool:
    count = sum(len(records) for records in payload.values())
    return count > MAX_BATCH_RECORDS or len(render_payload(payload).encode()) > MAX_BATCH_BYTES


def _pack_bundles(label: str, bundles: list[list[RecordItem]]) -> list[NamedBatch]:
    batches: list[NamedBatch] = []
    current: list[RecordItem] = []
    part = 1
    for bundle in bundles:
        candidate = _bundle_payload([*current, *bundle])
        if _exceeds_bounds(candidate) and current:
            batches.append((f"{label}-{part:03d}", _bundle_payload(current)))
            current = list(bundle)
            part += 1
        else:
            current.extend(bundle)
        if _exceeds_bounds(_bundle_payload(current)):
            raise ValueError(f"one {label} bundle exceeds seed bounds")
    if current:
        batches.append((f"{label}-{part:03d}", _bundle_payload(current)))
    return batches


def _owner_records(records: list[dict[str, object]], owner_key: str) -> dict[object, list]:
    result: dict[object, list] = {}
    for record in records:
        result.setdefault(record[owner_key], []).append(record)
    return result


def build_batches(payload: Payload) -> list[NamedBatch]:
    sources = {record["id"]: record for record in payload["sources"]}
    photo_ids = {record["id"] for record in payload["sources"] if record["type"] == "photo"}
    entity_links = _owner_records(payload["entity_sources"], "entity_id")
    texts = _owner_records(payload["entity_texts"], "entity_id")
    names = _owner_records(payload["entity_names"], "entity_id")
    relation_links = _owner_records(payload["relation_sources"], "relation_id")
    foundation = _bundle_payload(
        [("districts", row) for row in payload["districts"]]
        + [("sources", row) for row in payload["sources"] if row["id"] not in photo_ids]
    )
    entity_bundles = []
    for entity in payload["entities"]:
        links = entity_links.get(entity["id"], [])
        bundle = [("entities", entity)]
        bundle.extend(("entity_texts", row) for row in texts.get(entity["id"], []))
        bundle.extend(("entity_names", row) for row in names.get(entity["id"], []))
        bundle.extend(("entity_sources", row) for row in links if row["source_id"] not in photo_ids)
        bundle.extend(
            ("sources", sources[row["source_id"]])
            for row in links
            if row["source_id"] not in photo_ids
        )
        entity_bundles.append(bundle)
    relation_bundles = []
    for relation in payload["relations"]:
        links = relation_links.get(relation["id"], [])
        bundle = [("relations", relation)]
        bundle.extend(("relation_sources", row) for row in links)
        bundle.extend(("sources", sources[row["source_id"]]) for row in links)
        relation_bundles.append(bundle)
    evidence_bundles = [
        [("sources", sources[link["source_id"]]), ("entity_sources", link)]
        for link in payload["entity_sources"]
        if link["source_id"] in photo_ids
    ]
    return [
        ("foundation", foundation),
        *_pack_bundles("entities", entity_bundles),
        *_pack_bundles("relations", relation_bundles),
        *_pack_bundles("commons-evidence", evidence_bundles),
    ]


def rendered_batches(payload: Payload) -> dict[str, str]:
    return {
        f"{index:03d}-{label}.json": render_payload(batch)
        for index, (label, batch) in enumerate(build_batches(payload), start=1)
    }


def sync_output(output: Path, rendered: dict[str, str], *, check: bool) -> None:
    current = (
        {path.name: path.read_text(encoding="utf-8") for path in output.glob("*.json")}
        if output.is_dir()
        else {}
    )
    if check:
        if current != rendered:
            raise SystemExit(
                "catalog research batches are stale; run scripts/build_catalog_seed.py"
            )
        return
    output.mkdir(parents=True, exist_ok=True)
    for stale in set(current) - set(rendered):
        (output / stale).unlink()
    for name, content in rendered.items():
        (output / name).write_text(content, encoding="utf-8")

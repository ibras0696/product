import importlib.util
import json
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / "docs" / "test"
DATASET_PATH = RESEARCH_ROOT / "dataset.py"
HARVEST_PATH = RESEARCH_ROOT / "harvested_data.json"
MAPPINGS_PATH = RESEARCH_ROOT / "build_db.py"
OUTPUT_ROOT = ROOT / "backend" / "seeds" / "research_batches"
DEMO_OUTPUT_ROOT = ROOT / "backend" / "seeds" / "research_demo_batches"
CATEGORIES_ITOG_ROOT = RESEARCH_ROOT / "graph" / "categories_itog"
CATEGORIES_ITOG_OUTPUT_ROOT = ROOT / "backend" / "seeds" / "categories_itog_batches"
NAMESPACE = UUID("d608b8ce-99f7-4de6-9b9e-1f06036d9b19")
MAX_BATCH_RECORDS = 1_000
MAX_BATCH_BYTES = 2_000_000
GROUP_ORDER = (
    "districts",
    "sources",
    "entities",
    "entity_texts",
    "entity_names",
    "relations",
    "entity_sources",
    "relation_sources",
)
SOURCE_TYPES = {
    "academic": "scientific_article",
    "encyclopedia": "web_resource",
    "media": "web_resource",
    "media_repository": "web_resource",
    "museum": "museum_material",
    "official": "official_publication",
    "dataset": "web_resource",
}
PLACE_TYPES = {
    "city": "settlement",
    "town": "settlement",
    "village": "settlement",
    "locality": "settlement",
    "lake": "natural_object",
    "river": "natural_object",
    "mountain": "natural_object",
    "mosque": "cultural_object",
    "memorial": "cultural_object",
    "museum": "cultural_object",
    "fortress": "landmark",
    "tower_complex": "landmark",
}
RESIDENCE_TYPES = {
    "born": ("born_in", "Место рождения"),
    "lived": ("lived_in", "Место проживания"),
    "worked": ("worked_in", "Место работы"),
    "died": ("connected_with", "Место смерти"),
    "buried": ("connected_with", "Место захоронения"),
    "commemorated": ("connected_with", "Место увековечения памяти"),
}
Payload = dict[str, list[dict[str, object]]]


def stable_id(kind: str, *parts: str) -> str:
    return str(uuid5(NAMESPACE, ":".join((kind, *parts))))


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[ModuleType, dict[str, object], ModuleType]:
    dataset = _load_module(DATASET_PATH, "history_research_dataset")
    harvest = json.loads(HARVEST_PATH.read_text(encoding="utf-8"))
    mappings = _load_module(MAPPINGS_PATH, "history_research_mappings")
    return dataset, harvest, mappings


def empty_payload() -> Payload:
    return {name: [] for name in GROUP_ORDER}


def compact(*parts: object) -> str:
    return "\n\n".join(str(part).strip() for part in parts if part and str(part).strip())


def review_note(row: dict[str, object]) -> str:
    return f"Статус исследования: {row.get('verification_status') or 'needs_review'}."


def source_record(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": stable_id("source", str(row["slug"])),
        "title": row["title"],
        "type": SOURCE_TYPES[str(row["source_type"])],
        "author": None,
        "publisher": row.get("publisher"),
        "publication_year": None,
        "url": row.get("url"),
        "archive_reference": None,
        "description": row.get("notes") or "Источник исследовательского набора.",
        "is_verified": False,
        "status": "draft",
    }


def entity_record(
    kind: str,
    row: dict[str, object],
    entity_type: str,
    district_id: str | None = None,
    *,
    external: bool = False,
) -> dict[str, object]:
    identity = ("qid", str(row["external_id"])) if external else (str(row["slug"]),)
    period_from = row.get("birth_year") or row.get("start_year")
    period_to = row.get("death_year") or row.get("end_year")
    if period_from is not None and period_to is not None and period_from > period_to:
        period_from = None
        period_to = None
    return {
        "id": stable_id("entity", kind, *identity),
        "type": entity_type,
        "slug": row["slug"],
        "status": "draft",
        "district_id": district_id,
        "longitude": row.get("longitude"),
        "latitude": row.get("latitude"),
        "period_from": period_from,
        "period_to": period_to,
    }


def text_record(entity_id: str, title: object, short: object, full: object) -> dict[str, object]:
    return {
        "id": stable_id("entity-text", entity_id, "ru"),
        "entity_id": entity_id,
        "locale": "ru",
        "title": str(title),
        "short_description": str(short or "Исследовательский кандидат"),
        "full_description": str(full or "Исследовательский кандидат."),
    }


def name_records(
    entity_id: str, title: object, alternate: object = None, ce_title: object = None
) -> list[dict[str, object]]:
    names = [("ru", str(title))]
    names.extend(("ru", name.strip()) for name in str(alternate or "").split(";") if name.strip())
    if ce_title:
        names.append(("ce", str(ce_title)))
    return [
        {
            "id": stable_id("entity-name", entity_id, locale, name),
            "entity_id": entity_id,
            "locale": locale,
            "name": name,
        }
        for locale, name in names
    ]


def source_link(entity_id: str, source_slug: str) -> dict[str, object]:
    source_id = stable_id("source", source_slug)
    return {
        "id": stable_id("entity-source", entity_id, source_id),
        "entity_id": entity_id,
        "source_id": source_id,
    }

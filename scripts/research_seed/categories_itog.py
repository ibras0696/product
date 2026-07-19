import json
from pathlib import Path
from urllib.parse import unquote

from research_seed.common import Payload, compact, empty_payload, stable_id

SOURCE_TYPES = {
    "academic": "scientific_article",
    "archive": "archive_document",
    "dataset": "web_resource",
    "encyclopedia": "web_resource",
    "intergovernmental_report": "official_publication",
    "legal_document": "official_publication",
    "media": "web_resource",
    "official": "official_publication",
    "official_media": "official_publication",
    "primary_document": "archive_document",
}

DISTRICT_TITLES = {
    "achkhoy-martanovsky": "Ачхой-Мартановский район",
    "groznensky": "Грозненский район",
    "gudermessky": "Гудермесский район",
    "itum-kalinsky": "Итум-Калинский район",
    "kurchaloevsky": "Курчалоевский район",
    "nadterechny": "Надтеречный район",
    "naursky": "Наурский район",
    "nozhay-yurtovsky": "Ножай-Юртовский район",
    "shalinsky": "Шалинский район",
    "sharoysky": "Шаройский район",
    "shatoysky": "Шатойский район",
    "shelkovskoy": "Шелковской район",
    "sunzhensky": "Серноводский район",
    "urus-martanovsky": "Урус-Мартановский район",
    "vedensky": "Веденский район",
}


def load_categories(root: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(root.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        rows = document.get("items")
        if not isinstance(rows, list):
            raise ValueError(f"{path} must contain an items array")
        items.extend(rows)
    slugs = [str(item["slug"]) for item in items]
    if len(slugs) != len(set(slugs)):
        raise ValueError("categories_itog contains duplicate slugs")
    return items


def build_categories_payload(root: Path) -> Payload:
    items = load_categories(root)
    payload = empty_payload()
    entity_ids = {str(item["slug"]): stable_id("entity", str(item["slug"])) for item in items}
    _add_districts(payload, items)
    source_ids = _add_sources(payload, items)
    _add_entities(payload, items, entity_ids, source_ids)
    _add_relations(payload, items, entity_ids, source_ids)
    for records in payload.values():
        records.sort(key=lambda record: str(record["id"]))
    return payload


def _add_districts(payload: Payload, items: list[dict[str, object]]) -> None:
    slugs = sorted({str(item["district"]) for item in items if item.get("district")})
    payload["districts"] = [
        {
            "id": stable_id("district", slug),
            "slug": slug,
            "title_ru": DISTRICT_TITLES.get(slug, slug.replace("-", " ").title()),
            "title_ce": None,
        }
        for slug in slugs
    ]


def _all_source_details(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    details: dict[str, dict[str, object]] = {}
    for item in items:
        candidates = list(item.get("source_details") or [])
        for relation in item.get("relations") or []:
            candidates.extend(relation.get("source_details") or [])
        for source in candidates:
            slug = str(source["slug"])
            current = details.get(slug)
            if current is not None and current != source:
                merged = dict(current)
                for key, value in source.items():
                    if not merged.get(key) and value:
                        merged[key] = value
                details[slug] = merged
            else:
                details[slug] = source
    return details


def _add_sources(
    payload: Payload, items: list[dict[str, object]]
) -> dict[str, str]:
    source_ids: dict[str, str] = {}
    for slug, source in sorted(_all_source_details(items).items()):
        source_id = stable_id("source", slug)
        source_ids[slug] = source_id
        payload["sources"].append(
            {
                "id": source_id,
                "title": source.get("title") or slug,
                "type": SOURCE_TYPES.get(str(source.get("type")), "web_resource"),
                "author": None,
                "publisher": source.get("publisher"),
                "publication_year": None,
                "url": source.get("url"),
                "archive_reference": None,
                "description": compact(
                    source.get("title"),
                    f"Надёжность: {source.get('reliability') or 'не указана'}.",
                ),
                "is_verified": True,
                "status": "published",
            }
        )
    for item in items:
        photo = item.get("photo")
        if not isinstance(photo, dict):
            continue
        slug = f"photo:{item['slug']}"
        source_id = stable_id("source", slug)
        source_ids[slug] = source_id
        original_url = unquote(str(photo.get("url") or "")) or None
        archive_reference = (
            original_url if original_url is not None and len(original_url) <= 500 else None
        )
        payload["sources"].append(
            {
                "id": source_id,
                "title": f"Фотография: {item['name_ru']}",
                "type": "photo",
                "author": photo.get("author"),
                "publisher": "Wikimedia Commons" if photo.get("source_page") else None,
                "publication_year": None,
                "url": photo.get("source_page") or photo.get("url"),
                "archive_reference": archive_reference,
                "description": compact(
                    photo.get("license"), photo.get("license_url"), photo.get("source_page")
                ) or "Фотография объекта.",
                "is_verified": True,
                "status": "published",
            }
        )
    return source_ids


def _period(item: dict[str, object], key: str) -> int | None:
    value = item.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _add_entities(
    payload: Payload,
    items: list[dict[str, object]],
    entity_ids: dict[str, str],
    source_ids: dict[str, str],
) -> None:
    for item in items:
        slug = str(item["slug"])
        entity_id = entity_ids[slug]
        coordinate = item.get("coordinate") if isinstance(item.get("coordinate"), dict) else {}
        district = str(item["district"]) if item.get("district") else None
        description = str(item.get("description") or item["name_ru"])
        research_status = str(item.get("status") or "needs_review")
        full_description = compact(
            description,
            f"Статус исследования: {research_status}." if research_status != "verified" else None,
        )
        payload["entities"].append(
            {
                "id": entity_id,
                "type": item["type"],
                "slug": slug,
                "status": "published",
                "district_id": stable_id("district", district) if district else None,
                "longitude": coordinate.get("lon"),
                "latitude": coordinate.get("lat"),
                "period_from": _period(item, "period_from"),
                "period_to": _period(item, "period_to"),
            }
        )
        payload["entity_texts"].append(
            {
                "id": stable_id("entity-text", entity_id, "ru"),
                "entity_id": entity_id,
                "locale": "ru",
                "title": item["name_ru"],
                "short_description": description,
                "full_description": full_description,
            }
        )
        names = [item["name_ru"], *(item.get("aliases") or [])]
        if item.get("name_ce"):
            names.append(item["name_ce"])
        for name in dict.fromkeys(str(name).strip() for name in names if str(name).strip()):
            locale = "ce" if name == item.get("name_ce") else "ru"
            payload["entity_names"].append(
                {
                    "id": stable_id("entity-name", entity_id, locale, name),
                    "entity_id": entity_id,
                    "locale": locale,
                    "name": name,
                }
            )
        source_slugs = [str(source["slug"]) for source in item.get("source_details") or []]
        if isinstance(item.get("photo"), dict):
            source_slugs.append(f"photo:{slug}")
        for source_slug in dict.fromkeys(source_slugs):
            source_id = source_ids[source_slug]
            payload["entity_sources"].append(
                {
                    "id": stable_id("entity-source", entity_id, source_id),
                    "entity_id": entity_id,
                    "source_id": source_id,
                }
            )


def _add_relations(
    payload: Payload,
    items: list[dict[str, object]],
    entity_ids: dict[str, str],
    source_ids: dict[str, str],
) -> None:
    unique: dict[tuple[str, str, str], dict[str, object]] = {}
    for item in items:
        for relation in item.get("relations") or []:
            key = (str(relation["from"]), str(relation["to"]), str(relation["type"]))
            unique.setdefault(key, relation)
    for (source_slug, target_slug, relation_type), relation in unique.items():
        relation_id = stable_id("relation", source_slug, target_slug, relation_type)
        payload["relations"].append(
            {
                "id": relation_id,
                "source_entity_id": entity_ids[source_slug],
                "target_entity_id": entity_ids[target_slug],
                "type": relation_type,
                "title_ru": relation.get("title_ru") or "Связь",
                "title_ce": None,
                "description_ru": compact(
                    relation.get("title_ru"),
                    f"Уверенность: {relation.get('confidence') or 'не указана'}.",
                    f"Статус исследования: {relation.get('status') or 'needs_review'}.",
                ),
                "description_ce": None,
                "period_from": None,
                "period_to": None,
                "status": "published",
            }
        )
        for source in relation.get("source_details") or []:
            source_id = source_ids[str(source["slug"])]
            payload["relation_sources"].append(
                {
                    "id": stable_id("relation-source", relation_id, source_id),
                    "relation_id": relation_id,
                    "source_id": source_id,
                }
            )

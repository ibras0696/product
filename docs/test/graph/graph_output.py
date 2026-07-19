"""Запись производных JSON-файлов графа: категории интерфейса и хронология.

Чистые writer'ы поверх готовых узлов/рёбер. Логику сборки держит build_graph.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from graph_schema import CATEGORY_FILE, CATEGORY_TITLE, ENTITY_KIND


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_categories(
    out_dir: Path,
    grouped: dict[str, list[dict]],
    edges: list[dict],
    sources: list[dict],
) -> dict[str, int]:
    """Записать самодостаточные итоговые категории интерфейса.

    В карточке сохраняются исходные поля, полные источники и разрешённые связи
    с именами соседних объектов — отдельные nodes/edges для чтения не нужны.
    """
    all_nodes = {n["slug"]: n for items in grouped.values() for n in items}
    source_by_slug = {source["slug"]: source for source in sources}
    edges_by_slug: dict[str, list[dict]] = {}
    for edge in edges:
        edges_by_slug.setdefault(edge["from"], []).append(edge)
        edges_by_slug.setdefault(edge["to"], []).append(edge)
    buckets: dict[str, list[dict]] = {kind: [] for kind in CATEGORY_FILE}
    for items in grouped.values():
        for node in items:
            item = dict(node)
            item["source_details"] = [source_by_slug[s] for s in node["sources"]]
            item["relations"] = []
            for edge in edges_by_slug.get(node["slug"], []):
                outgoing = edge["from"] == node["slug"]
                related_slug = edge["to"] if outgoing else edge["from"]
                related = all_nodes[related_slug]
                relation = dict(edge)
                relation.update({
                    "direction": "outgoing" if outgoing else "incoming",
                    "related_slug": related_slug,
                    "related_name_ru": related["name_ru"],
                    "related_type": related["type"],
                    "source_details": [source_by_slug[s] for s in edge["sources"]],
                })
                item["relations"].append(relation)
            buckets[ENTITY_KIND[node["type"]]].append(item)
    (out_dir / "categories").mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for kind, filename in CATEGORY_FILE.items():
        nodes = sorted(buckets[kind], key=lambda n: n["slug"])
        write_json(out_dir / "categories" / f"{filename}.json", {
            "category": kind, "title_ru": CATEGORY_TITLE[kind],
            "count": len(nodes), "items": nodes,
        })
        counts[CATEGORY_TITLE[kind]] = len(nodes)
    return counts


def write_chronology(out_dir: Path, grouped: dict[str, list[dict]], edges: list[dict]) -> int:
    """Хронология: события по возрастанию даты со связанными местом и участниками."""
    names = {n["slug"]: n["name_ru"] for items in grouped.values() for n in items}
    events = grouped.get("events", [])
    event_slugs = {e["slug"] for e in events}
    place_of: dict[str, str] = {}
    participants: dict[str, list[str]] = {}
    for edge in edges:
        if edge["type"] == "located_in" and edge["from"] in event_slugs:
            place_of[edge["from"]] = names.get(edge["to"], edge["to"])
        if edge["type"] == "participated_in" and edge["to"] in event_slugs:
            participants.setdefault(edge["to"], []).append(names.get(edge["from"], edge["from"]))
    timeline = [
        {
            "period_from": ev.get("period_from"), "period_to": ev.get("period_to"),
            "date_text": ev.get("date_text"), "event_type": ev.get("event_type"),
            "slug": ev["slug"], "name_ru": ev["name_ru"], "description": ev["description"],
            "place": place_of.get(ev["slug"]), "participants": participants.get(ev["slug"], []),
            "photo": ev.get("photo"), "sources": ev.get("sources", []),
            "provenance": ev.get("provenance", {}), "status": ev.get("status"),
        }
        for ev in sorted(events, key=lambda x: (x.get("period_from") or 9999, x["slug"]))
    ]
    write_json(out_dir / "chronology.json", timeline)
    return len(timeline)

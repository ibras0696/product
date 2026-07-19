#!/usr/bin/env python3
"""Собирает граф «История Чечни» из sqlite.db в JSON-стандарт папки graph/.

Запуск:
    python3 docs/test/graph/build_graph.py            # читает docs/test/sqlite.db
    python3 docs/test/graph/build_graph.py --db /tmp/x.db --out /tmp/graph

Принципы (см. README.md):
- узлы и рёбра типизированы значениями backend-каталога (EntityType/RelationType),
  поэтому граф кладётся на catalog_entities/catalog_relations 1:1;
- в граф попадают только сущности, связанные с Чечнёй и её историей; всё
  остальное логируется в report.json как rejected_non_chechnya;
- пользовательский текст (`description`) — чистый: технические поля (ID, URL,
  точность координат, статус исследования) живут в отдельных полях, не в тексте;
- дедупликация выполняется в момент записи: узлы по (type, имя)/external_id,
  рёбра по (type, from, to), источники по ссылке — исходные файлы не меняются.

Зависимости: только стандартная библиотека (sqlite3, json, math).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from graph_dedup import dedup_edges, dedup_nodes
from graph_output import write_categories, write_chronology, write_json
from graph_schema import (  # словарь типов + гигиена текста
    CHECHNYA_KEYWORDS,
    GEO_CONFIRM_M,
    JUNK_MARKERS,
    NODE_FILE,
    PLACE_TYPE_TO_NODE,
    RESIDENCE_RELATION,
)
from graph_schema import aliases as _aliases
from graph_schema import clean_text as _clean_text
from graph_schema import in_chechnya as _in_chechnya
from graph_schema import looks_russian as _looks_russian
from graph_schema import norm as _norm
from graph_schema import place_description as _place_description
from graph_schema import provenance as _provenance

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE.parent / "sqlite.db"
DEFAULT_OUT = HERE  # курируемые overlay-файлы: HERE/curated_*.json

# JUNK_MARKERS/CHECHNYA_KEYWORDS реэкспортируются для тестов и читателей модуля.
__all__ = ["build", "CHECHNYA_KEYWORDS", "JUNK_MARKERS"]


class GraphBuilder:
    """Читает исходную БД и собирает узлы/рёбра графа с фильтром и дедупом."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.districts: dict[int, sqlite3.Row] = {}
        self.source_slug: dict[int, str] = {}
        self.place_node: dict[int, dict] = {}   # place_id -> node
        self.place_chechen: dict[int, bool] = {}
        self.person_node: dict[int, dict] = {}
        self.event_node: dict[int, dict] = {}
        self.artifact_node: dict[str, dict] = {}  # открытия/изобретения (overlay)
        self.overlay_sources: list[dict] = []
        self.evidence: dict[int, dict] = {}      # place_id -> лучшее OSM-свидетельство
        self.media: dict[tuple[str, int], dict] = {}  # (owner_type, id) -> фото
        self.edges: list[dict] = []
        self._russian_person_slugs: set[str] = set()
        self._synthetic_id = 0  # сквозные отрицательные id для overlay-людей
        self.report: dict[str, list] = {
            "rejected_non_chechnya": [], "rejected_russian_person": [],
            "weak_description": [], "low_confidence_relations": [],
            "ambiguous_birthplace": [], "deduplicated_nodes": [], "isolated_nodes": [],
            "enriched_nodes": [], "override_missing": [],
        }

    # ------------------------------------------- курируемый overlay (веб-факты)
    def _load_overlay(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.overlay_sources.extend(data.get("sources", []))
        for row in data.get("people", []):
            node = {
                "slug": row["slug"], "type": "person", "name_ru": row["name_ru"],
                "name_ce": row.get("name_ce"), "aliases": row.get("aliases", []),
                "description": _clean_text(row.get("description")),
                "category": row.get("category"), "title": row.get("title"),
                "occupation": row.get("occupation"),
                "period_from": row.get("period_from"), "period_to": row.get("period_to"),
                "birth_date": row.get("birth_date"), "death_date": row.get("death_date"),
                "external_id": row.get("external_id"),
                "provenance": row.get("provenance", {}), "sources": list(row.get("sources", [])),
                "photo": row.get("photo"),
                "status": row.get("status", "needs_review"), "_birthplace_id": None,
            }
            self._synthetic_id -= 1  # сквозной id, уникальный между overlay-файлами
            self.person_node[self._synthetic_id] = node
        for row in data.get("events", []):
            node = {
                "slug": row["slug"], "type": "event", "name_ru": row["name_ru"],
                "name_ce": row.get("name_ce"), "event_type": row.get("event_type", "historical"),
                "description": _clean_text(row.get("description")),
                "period_from": row.get("period_from"), "period_to": row.get("period_to"),
                "date_text": row.get("date_text"), "external_id": row.get("external_id"),
                "provenance": row.get("provenance", {}), "sources": list(row.get("sources", [])),
                "photo": row.get("photo"), "status": row.get("status", "needs_review"),
                "_place_id": None,
            }
            self._synthetic_id -= 1
            self.event_node[self._synthetic_id] = node
        for row in data.get("artifacts", []):
            self.artifact_node[row["slug"]] = {
                "slug": row["slug"], "type": "artifact", "name_ru": row["name_ru"],
                "name_ce": None, "description": _clean_text(row.get("description")),
                "field": row.get("field"), "kind": row.get("kind"),
                "period_from": row.get("period_from"), "period_to": row.get("period_to"),
                "external_id": row.get("external_id"),
                "provenance": row.get("provenance", {}), "sources": list(row.get("sources", [])),
                "status": row.get("status", "needs_review"),
            }
        for edge in data.get("relations", []):
            self._add_edge({**edge, "sources": list(edge.get("sources", []))})
        self._apply_overrides(data.get("overrides", []))

    def _apply_overrides(self, overrides: list[dict]) -> None:
        """Патчит поля существующих узлов по slug (обогащение биографий и т.п.)."""
        index: dict[str, dict] = {}
        for store in (self.place_node, self.person_node, self.event_node, self.artifact_node):
            for node in store.values():
                index[node["slug"]] = node
        for patch in overrides:
            node = index.get(patch["slug"])
            if node is None:
                self.report["override_missing"].append(patch["slug"])
                continue
            for key, value in patch.items():
                if key in ("slug", "sources"):
                    continue
                node[key] = _clean_text(value) if key == "description" else value
            for slug in patch.get("sources", []):
                if slug not in node["sources"]:
                    node["sources"].append(slug)
            self.report["enriched_nodes"].append(patch["slug"])

    # ------------------------------------------------------------------ load
    def _load_lookups(self) -> None:
        self.districts = {r["id"]: r for r in self.conn.execute("SELECT * FROM districts")}
        self.source_slug = {
            r["id"]: r["slug"] for r in self.conn.execute("SELECT id, slug FROM sources")
        }
        for r in self.conn.execute(
            "SELECT place_id, latitude, longitude, distance_m, source_url "
            "FROM coordinate_evidence ORDER BY distance_m"
        ):
            self.evidence.setdefault(r["place_id"], {
                "lat": r["latitude"], "lon": r["longitude"],
                "distance_m": round(r["distance_m"], 1), "url": r["source_url"],
            })
        for r in self.conn.execute(
            "SELECT place_id, person_id, event_id, original_url, file_page_url, "
            "license, license_url, artist FROM media_assets ORDER BY id"
        ):
            photo = {
                "url": r["original_url"], "source_page": r["file_page_url"],
                "license": r["license"], "license_url": r["license_url"],
                "author": r["artist"],
            }
            for owner_type, owner_id in (("place", r["place_id"]),
                                         ("person", r["person_id"]), ("event", r["event_id"])):
                if owner_id is not None:
                    self.media.setdefault((owner_type, owner_id), photo)  # первое фото

    def _src_list(self, source_id: int | None, extra: list[str] | None = None) -> list[str]:
        slugs: list[str] = []
        if source_id is not None and source_id in self.source_slug:
            slugs.append(self.source_slug[source_id])
        for slug in extra or []:
            if slug not in slugs:
                slugs.append(slug)
        return slugs

    # ----------------------------------------------------------------- nodes
    def _build_places(self) -> None:
        for row in self.conn.execute("SELECT * FROM places"):
            district = self.districts.get(row["district_id"])
            district_name = district["name_ru"] if district else None
            chechen = district is not None or _in_chechnya(row["latitude"], row["longitude"])
            description, weak = _place_description(row, district_name)
            evidence = self.evidence.get(row["id"])
            node_type = PLACE_TYPE_TO_NODE.get(row["place_type"], "settlement")
            coordinate = (
                {"lat": row["latitude"], "lon": row["longitude"]}
                if row["latitude"] is not None and row["longitude"] is not None else None
            )
            node = {
                "slug": row["slug"], "type": node_type, "name_ru": row["name_ru"],
                "name_ce": row["name_ce"], "aliases": _aliases(row["alt_names"]),
                "place_type": row["place_type"], "description": description,
                "district": district["slug"] if district else None,
                "coordinate": coordinate,
                "coordinate_accuracy": row["coordinate_accuracy"],
                "coordinate_precision_m": row["coordinate_precision_m"],
                "external_id": row["external_id"],
                "provenance": _provenance(
                    row["source_record_url"], row["coordinate_source_url"],
                    evidence if evidence and evidence["distance_m"] <= GEO_CONFIRM_M else None,
                ),
                "sources": self._src_list(row["source_id"], ["osm"] if evidence else None),
                "photo": self.media.get(("place", row["id"])),
                "status": row["verification_status"],
            }
            self.place_node[row["id"]] = node
            self.place_chechen[row["id"]] = chechen
            if weak:
                self.report["weak_description"].append(row["slug"])

    def _build_people(self) -> None:
        for row in self.conn.execute("SELECT * FROM people"):
            node = {
                "slug": row["slug"], "type": "person", "name_ru": row["full_name_ru"],
                "name_ce": row["full_name_ce"], "aliases": _aliases(row["alt_names"]),
                "description": _clean_text(row["biography"]),
                "category": row["category"], "title": row["title"],
                "occupation": row["occupation"],
                "period_from": row["birth_year"], "period_to": row["death_year"],
                "birth_date": row["birth_date"], "death_date": row["death_date"],
                "external_id": row["external_id"],
                "provenance": _provenance(row["source_record_url"], None, None),
                "sources": self._src_list(row["source_id"]),
                "photo": self.media.get(("person", row["id"])),
                "status": row["verification_status"],
                "_birthplace_id": row["birthplace_id"],
            }
            self.person_node[row["id"]] = node

    def _build_events(self) -> None:
        for row in self.conn.execute("SELECT * FROM events"):
            node = {
                "slug": row["slug"], "type": "event", "name_ru": row["name_ru"],
                "name_ce": None, "event_type": row["event_type"],
                "description": _clean_text(row["description"]),
                "period_from": row["start_year"], "period_to": row["end_year"],
                "date_text": row["date_text"], "external_id": row["external_id"],
                "provenance": _provenance(row["source_record_url"], None, None),
                "sources": self._src_list(row["source_id"]),
                "photo": self.media.get(("event", row["id"])),
                "status": row["verification_status"],
                "_place_id": row["place_id"],
            }
            self.event_node[row["id"]] = node

    # ----------------------------------------------------------------- edges
    def _born_in_confidence(self, place_id: int, status: str) -> tuple[str, float | None]:
        node = self.place_node.get(place_id)
        distance_km = None
        evidence = self.evidence.get(place_id)
        if evidence:
            distance_km = round(evidence["distance_m"] / 1000, 2)
        geo_ok = bool(node and node["coordinate"] and self.place_chechen.get(place_id))
        if geo_ok and (node["coordinate_accuracy"] in ("exact", "approximate")):
            return ("high" if status != "needs_review" else "medium"), distance_km
        return "medium", distance_km

    def _add_edge(self, edge: dict) -> None:
        self.edges.append(edge)
        if edge["confidence"] == "low":
            self.report["low_confidence_relations"].append(
                {"type": edge["type"], "from": edge["from"], "to": edge["to"]}
            )

    def _build_birthplace_edges(self) -> None:
        for person_id, node in self.person_node.items():
            place_id = node["_birthplace_id"]
            if not place_id or place_id not in self.place_node:
                continue
            confidence, distance_km = self._born_in_confidence(place_id, node["status"])
            evidence = {"method": "birthplace_id", "source": "birthplace_id"}
            if distance_km is not None:
                evidence["osm_distance_km"] = distance_km
            self._add_edge({
                "type": "born_in", "from": node["slug"], "to": self.place_node[place_id]["slug"],
                "title_ru": "Родился в", "period_from": None, "period_to": None,
                "evidence": evidence, "confidence": confidence,
                "sources": node["sources"], "status": node["status"],
            })

    def _build_residence_edges(self) -> None:
        rows = self.conn.execute("SELECT * FROM residences WHERE relation != 'born'")
        for row in rows:
            person, place = self.person_node.get(row["person_id"]), self.place_node.get(row["place_id"])
            if not person or not place:
                continue
            rel_type, title = RESIDENCE_RELATION[row["relation"]]
            status = row["verification_status"]
            self._add_edge({
                "type": rel_type, "from": person["slug"], "to": place["slug"],
                "title_ru": title, "period_from": None, "period_to": None,
                "evidence": {"method": "residences", "source": "residences"},
                "confidence": "high" if status == "verified" else "medium",
                "sources": self._src_list(row["source_id"]), "status": status,
            })

    def _build_participation_edges(self) -> None:
        for row in self.conn.execute("SELECT * FROM person_events"):
            person, event = self.person_node.get(row["person_id"]), self.event_node.get(row["event_id"])
            if not person or not event:
                continue
            self._add_edge({
                "type": "participated_in", "from": person["slug"], "to": event["slug"],
                "title_ru": row["role"] or "Участвовал в", "period_from": None, "period_to": None,
                "evidence": {"method": "person_events", "source": "person_events"},
                "confidence": "high" if row["verification_status"] == "verified" else "medium",
                "sources": self._src_list(row["source_id"]), "status": row["verification_status"],
            })
        for row in self.conn.execute("SELECT * FROM deeds WHERE event_id IS NOT NULL"):
            person, event = self.person_node.get(row["person_id"]), self.event_node.get(row["event_id"])
            if not person or not event:
                continue
            self._add_edge({
                "type": "participated_in", "from": person["slug"], "to": event["slug"],
                "title_ru": _clean_text(row["title"]) or "Участвовал в",
                "period_from": None, "period_to": None,
                "evidence": {"method": "deeds", "source": "deeds"},
                "confidence": "high" if row["verification_status"] == "verified" else "medium",
                "sources": self._src_list(row["source_id"]), "status": row["verification_status"],
            })

    def _build_event_location_edges(self) -> None:
        for node in self.event_node.values():
            place = self.place_node.get(node["_place_id"])
            if not place:
                continue
            self._add_edge({
                "type": "located_in", "from": node["slug"], "to": place["slug"],
                "title_ru": "Произошло в", "period_from": node["period_from"],
                "period_to": node["period_to"],
                "evidence": {"method": "events.place_id", "source": "events"},
                "confidence": "high" if node["status"] == "verified" else "medium",
                "sources": node["sources"], "status": node["status"],
            })

    def _build_text_birthplace_edges(self) -> None:
        """Инфо-привязка born_in из биографии для людей без birthplace_id."""
        settlements = {
            _norm(n["name_ru"]): (pid, n)
            for pid, n in self.place_node.items()
            if n["type"] == "settlement" and self.place_chechen.get(pid)
            and len(n["name_ru"]) >= 4
        }
        for node in self.person_node.values():
            if node["_birthplace_id"] or not node["description"]:
                continue
            text = f" {_norm(node['description'])} "
            hits = {pid: n for name, (pid, n) in settlements.items()
                    if f" {name} " in text}
            if len(hits) != 1:
                if len(hits) > 1:
                    self.report["ambiguous_birthplace"].append(node["slug"])
                continue
            pid, place = next(iter(hits.items()))
            confidence, distance_km = self._born_in_confidence(pid, node["status"])
            evidence = {"method": "biography_text", "source": "biography"}
            if distance_km is not None:
                evidence["osm_distance_km"] = distance_km
            self._add_edge({
                "type": "born_in", "from": node["slug"], "to": place["slug"],
                "title_ru": "Родился в", "period_from": None, "period_to": None,
                "evidence": evidence,
                "confidence": "low" if confidence == "medium" else "medium",
                "sources": node["sources"], "status": "needs_review",
            })

    # -------------------------------------------------- фильтр «только Чечня»
    @staticmethod
    def _is_curated(slug: str) -> bool:
        # Всё из dataset.py/deep_research — вручную отобранный чеченский корпус;
        # чисто массовые Wikidata-строки имеют slug вида "wd-q...".
        return not slug.startswith("wd-q")

    @staticmethod
    def _mentions_chechnya(node: dict) -> bool:
        blob = _norm(" ".join(filter(None, [node["name_ru"], node.get("description")])))
        return any(k in blob for k in CHECHNYA_KEYWORDS)

    def _place_is_chechen(self, place_id: int, node: dict) -> bool:
        # Внешние биографические места (Шлиссельбург, Караганда) остаются вне графа:
        # у них нет ни района, ни координат в Чечне, ни топонима-признака.
        return (
            self.place_chechen[place_id]
            or (self._is_curated(node["slug"]) and self._mentions_chechnya(node))
        )

    def _kept_slugs(self) -> set[str]:
        kept_place_slugs = {
            n["slug"] for pid, n in self.place_node.items() if self._place_is_chechen(pid, n)
        }
        edges_to: dict[str, set[str]] = {}
        for e in self.edges:
            edges_to.setdefault(e["from"], set()).add(e["to"])
        events_by_place = {
            n["slug"] for n in self.event_node.values()
            if self.place_node.get(n["_place_id"], {}).get("slug") in kept_place_slugs
        }
        # Русские (славянские) личности из массового слоя — не чеченский корпус.
        self._russian_person_slugs = {
            n["slug"] for n in self.person_node.values()
            if not self._is_curated(n["slug"]) and _looks_russian(n["name_ru"])
        }
        kept_people = set()
        for n in self.person_node.values():
            if n["slug"] in self._russian_person_slugs:
                continue
            birthplace = self.place_node.get(n["_birthplace_id"], {}).get("slug")
            linked = edges_to.get(n["slug"], set())
            if (self._is_curated(n["slug"]) or self._mentions_chechnya(n)
                    or birthplace in kept_place_slugs
                    or linked & (kept_place_slugs | events_by_place)):
                kept_people.add(n["slug"])
        kept_events = {
            n["slug"] for n in self.event_node.values() if self._is_curated(n["slug"])
        } | events_by_place
        for e in self.edges:
            if e["type"] == "participated_in" and e["from"] in kept_people:
                kept_events.add(e["to"])
        # Курируемые открытия/изобретения относятся к Чечне по построению.
        kept_artifacts = set(self.artifact_node)
        return kept_place_slugs | kept_people | kept_events | kept_artifacts

    def _log_rejections(self, kept: set[str]) -> None:
        groups = (self.place_node.values(), self.person_node.values(),
                  self.event_node.values(), self.artifact_node.values())
        for group in groups:
            for n in group:
                if n["slug"] in kept:
                    continue
                bucket = ("rejected_russian_person" if n["slug"] in self._russian_person_slugs
                          else "rejected_non_chechnya")
                self.report[bucket].append(
                    {"slug": n["slug"], "type": n["type"], "name": n["name_ru"]}
                )

    # ----------------------------------------------------------------- build
    def build(self, overlay_paths: tuple[Path, ...] = ()) -> tuple[dict[str, list[dict]], list[dict], list[str]]:
        self._load_lookups()
        self._build_places()
        self._build_people()
        self._build_events()
        self._build_birthplace_edges()
        self._build_residence_edges()
        self._build_participation_edges()
        self._build_event_location_edges()
        self._build_text_birthplace_edges()
        for overlay_path in overlay_paths:
            self._load_overlay(overlay_path)

        kept = self._kept_slugs()
        self._log_rejections(kept)
        all_nodes = [
            n for n in (*self.place_node.values(), *self.person_node.values(),
                        *self.event_node.values(), *self.artifact_node.values())
            if n["slug"] in kept
        ]
        nodes, remap, dedup_log = dedup_nodes(all_nodes)
        self.report["deduplicated_nodes"].extend(dedup_log)
        kept -= set(remap)
        edges = [e for e in self.edges if e["from"] in kept and e["to"] in kept]
        edges = dedup_edges(edges, remap)

        linked = {e["from"] for e in edges} | {e["to"] for e in edges}
        self.report["isolated_nodes"] = sorted(n["slug"] for n in nodes if n["slug"] not in linked)

        grouped: dict[str, list[dict]] = {name: [] for name in NODE_FILE.values()}
        for node in nodes:
            clean = {k: v for k, v in node.items() if not k.startswith("_")}
            grouped[NODE_FILE[node["type"]]].append(clean)
        used_sources = sorted(
            {s for n in nodes for s in n["sources"]} | {s for e in edges for s in e["sources"]}
        )
        return grouped, sorted(edges, key=lambda e: (e["type"], e["from"], e["to"])), used_sources

    def sources_payload(self, used: list[str]) -> list[dict]:
        rows = {r["slug"]: dict(r) for r in self.conn.execute("SELECT * FROM sources")}
        overlay = {row["slug"]: row for row in self.overlay_sources}
        payload = []
        for slug in used:
            row = rows.get(slug)
            if row is not None:
                payload.append({
                    "slug": row["slug"], "title": row["title"], "publisher": row["publisher"],
                    "url": row["url"], "type": row["source_type"], "reliability": row["reliability"],
                })
            elif slug in overlay:
                payload.append(overlay[slug])
            else:  # синтетический источник (osm) без строки в таблице/overlay
                payload.append({"slug": slug, "title": slug, "reliability": "medium"})
        return payload


def build(db_path: Path, out_dir: Path, overlay_paths: tuple[Path, ...] | None = None) -> dict:
    if overlay_paths is None:  # все курируемые overlay-файлы рядом с генератором
        overlay_paths = tuple(sorted(HERE.glob("curated_*.json")))
    conn = sqlite3.connect(db_path)
    builder = GraphBuilder(conn)
    grouped, edges, used_sources = builder.build(overlay_paths)
    sources = builder.sources_payload(used_sources)
    conn.close()

    (out_dir / "nodes").mkdir(parents=True, exist_ok=True)
    for name, items in grouped.items():
        write_json(out_dir / "nodes" / f"{name}.json", sorted(items, key=lambda n: n["slug"]))
    category_counts = write_categories(out_dir, grouped, edges, sources)
    write_chronology(out_dir, grouped, edges)
    write_json(out_dir / "edges.json", edges)
    write_json(out_dir / "sources.json", sources)

    edge_types: dict[str, int] = {}
    for edge in edges:
        edge_types[edge["type"]] = edge_types.get(edge["type"], 0) + 1
    summary = {
        "nodes_total": sum(len(v) for v in grouped.values()),
        "nodes_by_type": {name: len(items) for name, items in grouped.items()},
        "edges_total": len(edges), "edges_by_type": edge_types,
        "sources": len(sources),
        "rejected_non_chechnya": len(builder.report["rejected_non_chechnya"]),
        "rejected_russian_person": len(builder.report["rejected_russian_person"]),
        "weak_description": len(builder.report["weak_description"]),
        "low_confidence_relations": len(builder.report["low_confidence_relations"]),
        "ambiguous_birthplace": len(builder.report["ambiguous_birthplace"]),
        "deduplicated_nodes": len(builder.report["deduplicated_nodes"]),
        "isolated_nodes": len(builder.report["isolated_nodes"]),
        "categories": category_counts,
    }
    write_json(out_dir / "report.json", {"summary": summary, "details": builder.report})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка графа истории Чечни в JSON")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    summary = build(args.db, args.out)
    print(f"Граф собран: {args.out}")
    print(f"  узлов: {summary['nodes_total']}  {summary['nodes_by_type']}")
    print(f"  рёбер: {summary['edges_total']}  {summary['edges_by_type']}")
    print(f"  источников: {summary['sources']}")
    print(f"  отклонено (не Чечня): {summary['rejected_non_chechnya']}  "
          f"русских личностей убрано: {summary['rejected_russian_person']}")
    print(f"  слабых описаний: {summary['weak_description']}  "
          f"low-confidence связей: {summary['low_confidence_relations']}  "
          f"неоднозначных born_in: {summary['ambiguous_birthplace']}")
    print(f"  дедуп узлов: {summary['deduplicated_nodes']}  изолированных: {summary['isolated_nodes']}")
    print(f"  категории интерфейса: {summary['categories']}")


if __name__ == "__main__":
    main()

"""Дедупликация узлов и рёбер графа в момент записи.

Чистые функции без обращения к БД. Возвращают журнал слияний, чтобы вызывающий
код записал его в отчёт. Одноимённые далёкие места (в Чечне встречаются разные
сёла с одним названием) дубликатами не считаются — сливаются только совпадающие
по координатам (< 300 м) и записи с одинаковым external_id.
"""

from __future__ import annotations

from graph_schema import haversine_m, norm

COINCIDENT_M = 300.0


def _merge_sources(keep: dict, sources: list[str]) -> None:
    for slug in sources:
        if slug not in keep["sources"]:
            keep["sources"].append(slug)


def dedup_nodes(nodes: list[dict]) -> tuple[list[dict], dict[str, str], list[dict]]:
    chosen: dict[tuple, dict] = {}
    remap: dict[str, str] = {}
    log: list[dict] = []
    for node in sorted(nodes, key=lambda n: n["slug"]):
        key = ("id", node["external_id"]) if node["external_id"] else (
            node["type"], norm(node["name_ru"]))
        keep = chosen.get(key)
        if keep is None:
            chosen[key] = node
            continue
        _merge_sources(keep, node["sources"])
        remap[node["slug"]] = keep["slug"]
        log.append({"dropped": node["slug"], "kept": keep["slug"]})
    survivors, coincident, coincident_log = merge_coincident(list(chosen.values()))
    remap.update(coincident)
    return survivors, remap, log + coincident_log


def merge_coincident(nodes: list[dict]) -> tuple[list[dict], dict[str, str], list[dict]]:
    by_name: dict[tuple, list[dict]] = {}
    for node in nodes:
        by_name.setdefault((node["type"], norm(node["name_ru"])), []).append(node)
    remap: dict[str, str] = {}
    dropped: set[str] = set()
    log: list[dict] = []
    for group in by_name.values():
        for index, keep in enumerate(group):
            if keep["slug"] in dropped or not keep.get("coordinate"):
                continue
            for other in group[index + 1:]:
                coord = other.get("coordinate")
                if other["slug"] in dropped or not coord:
                    continue
                distance = haversine_m(
                    keep["coordinate"]["lat"], keep["coordinate"]["lon"],
                    coord["lat"], coord["lon"],
                )
                if distance < COINCIDENT_M:
                    _merge_sources(keep, other["sources"])
                    remap[other["slug"]] = keep["slug"]
                    dropped.add(other["slug"])
                    log.append({"dropped": other["slug"], "kept": keep["slug"],
                                "reason": "coincident"})
    return [n for n in nodes if n["slug"] not in dropped], remap, log


def dedup_edges(edges: list[dict], remap: dict[str, str]) -> list[dict]:
    rank = {"high": 3, "medium": 2, "low": 1}
    chosen: dict[tuple, dict] = {}
    for edge in edges:
        edge = dict(edge)
        edge["from"] = remap.get(edge["from"], edge["from"])
        edge["to"] = remap.get(edge["to"], edge["to"])
        if edge["from"] == edge["to"]:
            continue
        key = (edge["type"], edge["from"], edge["to"])
        keep = chosen.get(key)
        if keep is None or rank[edge["confidence"]] > rank[keep["confidence"]]:
            if keep:
                _merge_sources(edge, keep["sources"])
            chosen[key] = edge
        else:
            _merge_sources(keep, edge["sources"])
    return list(chosen.values())

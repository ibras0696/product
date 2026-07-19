"""Проверки графа: целостность связей, фильтр Чечни, чистота текста, дедуп.

Граф пересобирается во временную папку из исходной docs/test/sqlite.db, поэтому
тест проверяет генератор, а не закоммиченный артефакт.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_graph import CHECHNYA_KEYWORDS, JUNK_MARKERS, build  # noqa: E402
from graph_schema import CATEGORY_FILE, ENTITY_KIND, looks_russian  # noqa: E402

DB_PATH = HERE.parent / "sqlite.db"
ENTITY_TYPES = {
    "settlement", "person", "event", "landmark", "natural_object",
    "cultural_object", "organization", "university_object", "artifact",
}
RELATION_TYPES = {
    "born_in", "lived_in", "worked_in", "studied_in", "taught_at",
    "participated_in", "located_in", "part_of", "created_by",
    "described_in", "connected_with", "connected_with_chgu",
}


class GraphBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        out = Path(cls.tempdir.name)
        cls.summary = build(DB_PATH, out)
        cls.nodes = []
        for path in sorted((out / "nodes").glob("*.json")):
            cls.nodes.extend(json.loads(path.read_text(encoding="utf-8")))
        cls.edges = json.loads((out / "edges.json").read_text(encoding="utf-8"))
        cls.sources = json.loads((out / "sources.json").read_text(encoding="utf-8"))
        cls.by_slug = {n["slug"]: n for n in cls.nodes}
        cls.chronology = json.loads((out / "chronology.json").read_text(encoding="utf-8"))
        cls.categories = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((out / "categories").glob("*.json"))
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_graph_is_the_core_output_with_hero_to_village_links(self):
        born_in = [e for e in self.edges if e["type"] == "born_in"]
        self.assertGreaterEqual(len(born_in), 280)
        for edge in born_in:
            person = self.by_slug[edge["from"]]
            settlement = self.by_slug[edge["to"]]
            self.assertEqual(person["type"], "person")
            self.assertEqual(settlement["type"], "settlement")
            self.assertIn(edge["confidence"], ("high", "medium", "low"))

    def test_every_edge_references_existing_distinct_nodes(self):
        for edge in self.edges:
            self.assertIn(edge["from"], self.by_slug, edge)
            self.assertIn(edge["to"], self.by_slug, edge)
            self.assertNotEqual(edge["from"], edge["to"], edge)
            self.assertIn(edge["type"], RELATION_TYPES, edge)

    def test_node_types_map_to_catalog_entity_types(self):
        for node in self.nodes:
            self.assertIn(node["type"], ENTITY_TYPES, node["slug"])

    def test_non_chechnya_entities_are_excluded_and_logged(self):
        # Внешние биографические места не попадают в граф, но видны в отчёте.
        for external in ("shlisselburg", "karaganda", "brest-fortress"):
            self.assertNotIn(external, self.by_slug)
        self.assertGreater(self.summary["rejected_non_chechnya"], 0)

    def test_user_facing_text_has_no_technical_junk(self):
        for node in self.nodes:
            description = node.get("description") or ""
            for marker in JUNK_MARKERS:
                self.assertNotIn(marker, description, node["slug"])

    def test_provenance_does_not_duplicate_identical_urls(self):
        for node in self.nodes:
            provenance = node.get("provenance") or {}
            record = provenance.get("record_url")
            coordinate = provenance.get("coordinate_source_url")
            if record is not None and coordinate is not None:
                self.assertNotEqual(record, coordinate, node["slug"])

    def test_nodes_and_edges_are_deduplicated(self):
        slugs = [n["slug"] for n in self.nodes]
        self.assertEqual(len(slugs), len(set(slugs)))
        keys = [(e["type"], e["from"], e["to"]) for e in self.edges]
        self.assertEqual(len(keys), len(set(keys)))

    def test_geo_confirmation_is_recorded_for_birthplace_links(self):
        # Хотя бы часть born_in имеет гео-свидетельство (инфо + гео).
        with_geo = [
            e for e in self.edges
            if e["type"] == "born_in" and "osm_distance_km" in e["evidence"]
        ]
        self.assertGreater(len(with_geo), 0)

    def test_every_source_used_is_described(self):
        described = {s["slug"] for s in self.sources}
        for node in self.nodes:
            for slug in node["sources"]:
                self.assertIn(slug, described, node["slug"])

    def test_curated_heroes_survive_the_chechnya_filter(self):
        for hero in ("dachiev", "beybulatov", "visaitov"):
            self.assertIn(hero, self.by_slug, hero)

    def test_russian_personalities_are_removed_from_persons(self):
        harvested_people = [
            n for n in self.nodes
            if n["type"] == "person" and n["slug"].startswith("wd-q")
        ]
        russian = [n for n in harvested_people if looks_russian(n["name_ru"])]
        self.assertEqual(russian, [], [n["name_ru"] for n in russian])
        # авторы открытий (чеченские фамилии) при этом сохранены
        for author in ("wd-q4503614", "wd-q4494545"):
            self.assertIn(author, self.by_slug, author)

    def test_keyword_signal_is_non_empty(self):
        self.assertIn("чечен", CHECHNYA_KEYWORDS)

    def test_discoveries_are_linked_to_authors_via_created_by(self):
        artifacts = [n for n in self.nodes if n["type"] == "artifact"]
        self.assertGreaterEqual(len(artifacts), 3)
        created_by = [e for e in self.edges if e["type"] == "created_by"]
        # каждое открытие/изобретение привязано к личности-автору
        for edge in created_by:
            self.assertEqual(self.by_slug[edge["from"]]["type"], "artifact")
            self.assertEqual(self.by_slug[edge["to"]]["type"], "person")
            self.assertTrue(edge["sources"], edge)
        linked_artifacts = {e["from"] for e in created_by}
        for artifact in artifacts:
            self.assertIn(artifact["slug"], linked_artifacts, artifact["slug"])

    def test_category_split_matches_backend_kinds_without_losing_nodes(self):
        # Пять категорий интерфейса; ни один узел не потерян и не задвоен.
        self.assertEqual(set(self.categories), set(CATEGORY_FILE.values()))
        placed = []
        for payload in self.categories.values():
            self.assertEqual(payload["count"], len(payload["items"]))
            placed.extend(payload["items"])
        self.assertEqual(len(placed), len(self.nodes))
        self.assertEqual({n["slug"] for n in placed}, set(self.by_slug))

    def test_each_node_lands_in_the_kind_backend_assigns(self):
        file_by_kind = {v: k for k, v in CATEGORY_FILE.items()}
        for stem, payload in self.categories.items():
            kind = file_by_kind[stem]
            for node in payload["items"]:
                self.assertEqual(ENTITY_KIND[node["type"]], kind, node["slug"])

    def test_final_event_category_contains_sources_and_resolved_relations(self):
        events = self.categories["sobytiya"]["items"]
        by_slug = {event["slug"]: event for event in events}
        agreement = by_slug["khasavyurt-accords-1996"]
        self.assertTrue(agreement["source_details"])
        self.assertTrue(all(source.get("url") for source in agreement["source_details"]))
        maskhadov = [
            relation for relation in agreement["relations"]
            if relation["related_slug"] == "maskhadov-aslan"
        ]
        self.assertEqual(len(maskhadov), 1)
        self.assertEqual(maskhadov[0]["related_name_ru"], "Аслан Алиевич Масхадов")
        self.assertEqual(maskhadov[0]["direction"], "incoming")
        self.assertTrue(maskhadov[0]["source_details"])

    def test_people_photos_are_licensed_commons_urls(self):
        with_photo = [n for n in self.nodes if n.get("photo")]
        self.assertGreater(len(with_photo), 0)
        for node in with_photo:
            photo = node["photo"]
            self.assertTrue(photo["url"].startswith("https://"), node["slug"])
            self.assertIn("license", photo)

    def test_curated_discoveries_carry_sources(self):
        described = {s["slug"] for s in self.sources}
        for node in self.nodes:
            if node["type"] == "artifact":
                self.assertTrue(node["sources"], node["slug"])
                for slug in node["sources"]:
                    self.assertIn(slug, described, node["slug"])

    def test_chronology_covers_major_historical_transitions(self):
        by_slug = {event["slug"]: event for event in self.chronology}
        expected = {
            "chechen-autonomous-oblast-1922",
            "abolition-chechen-ingush-assr-1944",
            "restoration-chechen-ingush-assr-1957",
            "khasavyurt-accords-1996",
            "chechen-constitution-referendum-2003",
            "end-cto-chechnya-2009",
        }
        self.assertTrue(expected <= set(by_slug), expected - set(by_slug))
        self.assertEqual(by_slug["restoration-chechen-ingush-assr-1957"]["date_text"], "9 января 1957")
        self.assertEqual(by_slug["khasavyurt-accords-1996"]["event_type"], "peace_agreement")

    def test_chronology_is_sorted_and_keeps_fact_provenance(self):
        years = [event["period_from"] or 9999 for event in self.chronology]
        self.assertEqual(years, sorted(years))
        described = {source["slug"] for source in self.sources}
        for event in self.chronology:
            self.assertTrue(event["sources"], event["slug"])
            self.assertTrue(set(event["sources"]) <= described, event["slug"])
            self.assertTrue(event["provenance"].get("record_url"), event["slug"])


if __name__ == "__main__":
    unittest.main()

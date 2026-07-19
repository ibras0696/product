import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_db import build


class ResearchDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "research.db"
        self.counts = build(self.db_path)
        self.connection = sqlite3.connect(self.db_path)

    def tearDown(self):
        self.connection.close()
        self.tempdir.cleanup()

    def scalar(self, query, parameters=()):
        return self.connection.execute(query, parameters).fetchone()[0]

    def test_harvest_expands_the_reviewable_corpus(self):
        self.assertGreaterEqual(self.counts["places"], 750)
        self.assertGreaterEqual(self.counts["people"], 400)
        self.assertGreaterEqual(self.counts["events"], 40)
        self.assertGreaterEqual(self.counts["media_assets"], 400)
        self.assertGreaterEqual(self.counts["coordinate_evidence"], 400)
        self.assertGreaterEqual(self.counts["source_documents"], 15)
        self.assertGreaterEqual(self.counts["fact_citations"], 15)
        self.assertEqual(self.scalar("PRAGMA integrity_check"), "ok")
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_external_entities_are_deduplicated_and_sourced(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM districts WHERE source_id IS NULL"), 0)
        for table in ("places", "people", "events"):
            duplicates = self.scalar(
                f"""SELECT COUNT(*) FROM (
                       SELECT external_id FROM {table}
                       WHERE external_id IS NOT NULL
                       GROUP BY external_id HAVING COUNT(*) > 1
                   )"""
            )
            unsourced = self.scalar(
                f"""SELECT COUNT(*) FROM {table}
                    WHERE source_id IS NULL OR source_record_url IS NULL"""
            )
            self.assertEqual(duplicates, 0, table)
            self.assertEqual(unsourced, 0, table)

    def test_coordinates_expose_accuracy_and_provenance(self):
        located = self.scalar(
            "SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        sourced = self.scalar(
            """SELECT COUNT(*) FROM places
               WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                 AND coordinate_accuracy IN ('exact', 'approximate')
                 AND coordinate_source_url IS NOT NULL"""
        )
        self.assertGreaterEqual(located, 750)
        self.assertEqual(sourced, located)
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM places
                   WHERE latitude NOT BETWEEN -90 AND 90
                      OR longitude NOT BETWEEN -180 AND 180"""
            ),
            0,
        )

    def test_media_keeps_rights_and_owner_links(self):
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM media_assets
                   WHERE file_page_url NOT LIKE 'https://commons.wikimedia.org/%'
                      OR original_url NOT LIKE 'https://upload.wikimedia.org/%'
                      OR license IS NULL"""
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM media_assets
                   WHERE (place_id IS NOT NULL) + (person_id IS NOT NULL) +
                         (event_id IS NOT NULL) != 1"""
            ),
            0,
        )

    def test_relationships_are_reviewable_and_sourced(self):
        for table in ("residences", "person_events"):
            self.assertEqual(
                self.scalar(
                    f"""SELECT COUNT(*) FROM {table}
                        WHERE source_id IS NULL OR verification_status NOT IN
                        ('verified', 'corroborated', 'needs_review')"""
                ),
                0,
                table,
            )

    def test_impossible_life_periods_are_not_kept(self):
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM people
                   WHERE birth_year IS NOT NULL AND death_year IS NOT NULL
                     AND birth_year > death_year"""
            ),
            0,
        )
        visaitov = self.connection.execute(
            "SELECT birth_date FROM people WHERE slug = 'visaitov'"
        ).fetchone()
        self.assertEqual(visaitov[0], "1914-05-13")

    def test_current_administrative_statuses_are_preserved(self):
        district = self.connection.execute(
            "SELECT name_ru, notes FROM districts WHERE slug = 'sunzhensky'"
        ).fetchone()
        self.assertEqual(district[0], "Серноводский район")
        self.assertIn("Сунженский", district[1])
        city_types = dict(self.connection.execute(
            "SELECT slug, place_type FROM places WHERE slug IN ('achkhoy-martan', 'sernovodskoye')"
        ))
        self.assertEqual(city_types, {"achkhoy-martan": "city", "sernovodskoye": "city"})

    def test_claim_level_citations_point_to_one_subject(self):
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM fact_citations
                   WHERE (place_id IS NOT NULL) + (person_id IS NOT NULL) +
                         (event_id IS NOT NULL) + (deed_id IS NOT NULL) != 1"""
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM fact_citations fc
                   JOIN source_documents sd ON sd.id = fc.document_id
                   WHERE sd.url NOT LIKE 'http%' OR fc.claim_summary = ''"""
            ),
            0,
        )

    def test_osm_is_independent_evidence_not_a_silent_overwrite(self):
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM coordinate_evidence
                   WHERE provider != 'OpenStreetMap' OR source_url NOT LIKE
                         'https://www.openstreetmap.org/%' OR distance_m < 0"""
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM coordinate_evidence ce
                   JOIN places p ON p.id = ce.place_id
                   WHERE ce.verification_status = 'corroborated' AND ce.distance_m > 1000"""
            ),
            0,
        )

    def test_aggregator_sources_are_not_ranked_as_high(self):
        self.assertEqual(
            self.scalar(
                """SELECT COUNT(*) FROM sources
                   WHERE publisher IN ('Википедия', 'Wikipedia') AND reliability = 'high'"""
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()

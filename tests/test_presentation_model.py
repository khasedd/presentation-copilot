"""Representation guarantees against a synthetic API response."""
import json
import unittest
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path

from presentation.adapters.google_slides import normalize_presentation
from presentation.model import SourceRevision, deck_to_json, validate_deck

FIXTURE = Path(__file__).parent / "fixtures/google_slides_presentation.json"
NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())
        self.deck = normalize_presentation(self.payload, fetched_at=NOW)

    def test_serializes_version_provenance_revision_and_local_references(self):
        doc = json.loads(deck_to_json(self.deck))
        self.assertEqual(doc["schema_version"], "1.0")
        self.assertEqual(doc["provenance"]["source_document_id"], "synthetic_deck")
        self.assertEqual(doc["source_revision"]["revision_id"], "opaque-revision-A")
        self.assertEqual(doc["source_revision"]["fetched_at"], "2026-09-25T00:00:00+00:00")
        self.assertEqual([s["position"] for s in doc["slides"]], [0, 1, 2])
        self.assertEqual(doc["slides"][0]["id"], "slide/0")
        self.assertEqual(doc["slides"][0]["concepts"], [])
        self.assertEqual(doc["slides"][0]["concept_status"], "not_extracted")
        self.assertEqual([f.name for f in fields(SourceRevision)], ["revision_id", "fetched_at"])
        self.assertEqual(deck_to_json(self.deck), deck_to_json(self.deck))

    def test_snapshot_ignores_observation_time_and_revision_token(self):
        self.payload["revisionId"] = "different-token"
        newer = normalize_presentation(self.payload, fetched_at=NOW.replace(day=26))
        self.assertEqual(self.deck.snapshot_id, newer.snapshot_id)
        self.assertNotEqual(self.deck.source_revision, newer.source_revision)

    def test_fingerprint_excludes_position_and_source_ids_but_snapshot_does_not(self):
        slide = self.payload["slides"].pop(0)
        slide["objectId"] = "replacement_slide"
        slide["pageElements"][0]["objectId"] = "replacement_element"
        self.payload["slides"].append(slide)
        newer = normalize_presentation(self.payload, fetched_at=NOW)
        self.assertEqual(self.deck.slides[0].content_fingerprint, newer.slides[2].content_fingerprint)
        self.assertNotEqual(self.deck.snapshot_id, newer.snapshot_id)

    def test_rejects_naive_timestamp_and_invalid_schema_order_or_digest(self):
        with self.assertRaises(ValueError):
            SourceRevision(None, datetime(2026, 9, 25))
        for deck in (
            replace(self.deck, schema_version="2.0"),
            replace(self.deck, slides=tuple(reversed(self.deck.slides))),
            replace(self.deck, snapshot_id="incorrect"),
        ):
            with self.subTest(deck=deck.schema_version), self.assertRaises(ValueError):
                validate_deck(deck)

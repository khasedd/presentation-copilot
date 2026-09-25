"""Deterministic correspondence does not claim persistent identity."""
import copy
import unittest
from datetime import datetime, timezone

from presentation.adapters.google_slides import normalize_presentation
from presentation.comparison import compare_snapshots

NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)


def slide(source_id, text):
    return {"objectId": source_id, "pageElements": [
        {"objectId": source_id + "_text", "shape": {"text": {"textElements": [
            {"textRun": {"content": text}}
        ]}}}
    ], "slideProperties": {"notesPage": {
        "objectId": source_id + "_notes", "notesProperties": {
            "speakerNotesObjectId": source_id + "_speaker"}, "pageElements": []}}}


def deck(slides, **extra):
    return normalize_presentation({"presentationId": "deck", "slides": slides, **extra}, fetched_at=NOW)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.c = slide("aaa", "Alpha"), slide("bbb", "Beta"), slide("ccc", "Gamma")

    def test_unchanged_and_revision_only_changes(self):
        result = compare_snapshots(deck([self.a, self.b]), deck([self.a, self.b], revisionId="new"))
        self.assertEqual(len(result.matches), 2)
        self.assertFalse(result.order_changed)
        self.assertFalse(result.added or result.removed or result.ambiguous)
        self.assertTrue(all(not m.content_changed and not m.provenance_changed for m in result.matches))

    def test_reorder_is_distinct_from_position_shift_due_to_insertion_or_deletion(self):
        old = deck([self.a, self.b])
        reordered = compare_snapshots(old, deck([self.b, self.a]))
        self.assertTrue(reordered.order_changed)
        self.assertEqual([(m.previous_position, m.current_position) for m in reordered.matches], [(0, 1), (1, 0)])
        inserted = compare_snapshots(old, deck([self.c, self.a, self.b]))
        self.assertFalse(inserted.order_changed)
        self.assertEqual(inserted.added, ("slide/0",))
        deleted = compare_snapshots(old, deck([self.b]))
        self.assertFalse(deleted.order_changed)
        self.assertEqual(deleted.removed, ("slide/0",))

    def test_same_id_edit_and_reorder_are_independent(self):
        changed = slide("aaa", "Alpha revised")
        result = compare_snapshots(deck([self.a, self.b]), deck([self.b, changed]))
        self.assertTrue(result.order_changed)
        self.assertTrue(result.matches[0].content_changed)
        self.assertEqual(result.matches[0].basis, "source_id")
        self.assertEqual(result.matches[0].reuse, "invalidate")

    def test_notes_edit_invalidates(self):
        changed = copy.deepcopy(self.a)
        changed["slideProperties"]["notesPage"]["pageElements"] = [{
            "objectId": "aaa_speaker", "shape": {"text": {"textElements": [
                {"textRun": {"content": "New presenter intention"}}
            ]}}}]
        result = compare_snapshots(deck([self.a]), deck([changed]))
        self.assertTrue(result.matches[0].content_changed)
        self.assertEqual(result.matches[0].reuse, "invalidate")

    def test_unique_content_matches_replacement_ids_but_requires_rebinding(self):
        result = compare_snapshots(deck([self.a]), deck([slide("replacement", "Alpha")]))
        self.assertEqual(result.matches[0].basis, "content_fingerprint")
        self.assertFalse(result.matches[0].content_changed)
        self.assertTrue(result.matches[0].provenance_changed)
        self.assertEqual(result.matches[0].reuse, "rebind_required")

    def test_element_replacement_with_retained_slide_id_requires_rebinding(self):
        changed = copy.deepcopy(self.a)
        changed["pageElements"][0]["objectId"] = "replacement_element"
        match = compare_snapshots(deck([self.a]), deck([changed])).matches[0]
        self.assertTrue(match.provenance_changed)
        self.assertEqual(match.reuse, "rebind_required")

    def test_duplicate_candidates_are_ambiguous_not_added_removed_or_position_matched(self):
        old = deck([self.a, slide("duplicate", "Alpha")])
        new = deck([slide("replacement", "Alpha")])
        result = compare_snapshots(old, new)
        self.assertFalse(result.matches or result.added or result.removed)
        self.assertEqual(result.ambiguous[0].previous_ids, ("slide/0", "slide/1"))
        self.assertEqual(result.ambiguous[0].current_ids, ("slide/0",))
        self.assertEqual(result, compare_snapshots(old, new))

    def test_changed_id_and_content_are_add_remove(self):
        result = compare_snapshots(deck([self.a]), deck([slide("replacement", "Changed")]))
        self.assertFalse(result.matches)
        self.assertEqual(result.added, ("slide/0",))
        self.assertEqual(result.removed, ("slide/0",))

    def test_empty_or_visual_only_slides_never_match_by_content(self):
        for content in ([], [{"objectId": "image", "description": "Diagram", "image": {}}]):
            old = deck([{"objectId": "old", "pageElements": content}])
            new = deck([{"objectId": "new", "pageElements": content}])
            result = compare_snapshots(old, new)
            self.assertFalse(result.matches)
            self.assertEqual(len(result.added), 1)

    def test_incomplete_extraction_requires_review_even_with_same_id(self):
        visual = {"objectId": "visual", "pageElements": [{"objectId": "image", "image": {}}]}
        result = compare_snapshots(deck([visual]), deck([visual]))
        self.assertEqual(result.matches[0].reuse, "review_required")
        self.assertTrue(result.issues)

    def test_different_source_rejected(self):
        other = normalize_presentation({"presentationId": "other", "slides": []}, fetched_at=NOW)
        with self.assertRaises(ValueError):
            compare_snapshots(deck([]), other)

"""Offline normalization, transport and CLI integration tests."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from presentation.adapters.google_slides import GoogleSlidesSource, _NoRedirect, normalize_presentation
from presentation.source import PresentationSourceError
from experiments.ingest_google_slides import main

FIXTURE = Path(__file__).parent / "fixtures/google_slides_presentation.json"
NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def test_preserves_text_groups_tables_notes_and_source_ids(self):
        result = normalize_presentation(self.payload, fetched_at=NOW)
        first = result.slides[0]
        self.assertEqual(first.provenance.source_page_id, "slide_intro")
        self.assertEqual(first.elements[0].text, "Hello 世界\nSecond paragraph\n")
        self.assertEqual(first.elements[1].children[0].text, "Nested content\n")
        self.assertEqual([c.text for c in first.elements[2].table_cells], ["Left\n", "Right\n"])
        self.assertEqual(first.elements[2].table_cells[1].column, 1)
        self.assertEqual(first.speaker_notes.text, "Presenter-authored explanation.\n")
        self.assertEqual(first.speaker_notes.provenance.source_page_id, "notes_intro")
        self.assertEqual(first.speaker_notes.provenance.source_object_id, "speaker_intro")
        self.assertEqual(result.slides[1].speaker_notes.status, "empty")
        self.assertEqual(result.slides[2].speaker_notes.status, "unavailable")
        self.assertEqual(result.slides[1].elements[0].alt_title, "Architecture")
        self.assertEqual(result.slides[1].elements[1].kind, "chart")
        self.assertEqual(result.slides[1].elements[1].extraction_status, "unsupported")
        self.assertTrue(result.issues)

    def test_missing_revision_and_empty_deck_are_valid_and_input_is_not_mutated(self):
        before = copy.deepcopy(self.payload)
        normalize_presentation(self.payload, fetched_at=NOW)
        self.assertEqual(self.payload, before)
        empty = normalize_presentation({"presentationId": "empty"}, fetched_at=NOW)
        self.assertEqual(empty.slides, ())
        self.assertIsNone(empty.source_revision.revision_id)

    def test_word_art_auto_text_and_unknown_elements(self):
        self.payload["slides"][0]["pageElements"] = [
            {"objectId": "wordart", "wordArt": {"renderedText": "Display text"}},
            {"objectId": "auto", "shape": {"text": {"textElements": [{"autoText": {"content": "1"}}]}}},
            {"objectId": "future", "futureElement": {"data": "unknown"}},
        ]
        elements = normalize_presentation(self.payload, fetched_at=NOW).slides[0].elements
        self.assertEqual([e.text for e in elements], ["Display text", "1", ""])
        self.assertEqual(elements[2].kind, "unknown")
        self.assertEqual(elements[2].extraction_status, "unsupported")

    def test_merged_table_cells_preserve_coordinates_and_spans(self):
        table = self.payload["slides"][0]["pageElements"][2]["table"]
        table["rows"] = 2
        table["tableRows"] = [{"tableCells": [{
            "location": {}, "rowSpan": 2, "columnSpan": 2,
            "text": {"textElements": [{"textRun": {"content": "Merged\n"}}]},
        }]}, {}]
        element = normalize_presentation(self.payload, fetched_at=NOW).slides[0].elements[2]
        cell = element.table_cells[0]
        self.assertEqual((cell.row, cell.column, cell.row_span, cell.column_span), (0, 0, 2, 2))
        self.assertEqual((element.table_rows, element.table_columns), (2, 2))
        self.assertEqual(cell.text, "Merged\n")
        for invalid in (0, -1, True, 3):
            table["tableRows"][0]["tableCells"][0]["columnSpan"] = invalid
            with self.subTest(span=invalid), self.assertRaises(PresentationSourceError):
                normalize_presentation(self.payload, fetched_at=NOW)

    def test_unknown_text_marks_group_partial_and_notes_unavailable(self):
        first = self.payload["slides"][0]
        first["pageElements"][1]["elementGroup"]["children"][0]["shape"]["text"]["textElements"].append({"futureText": {}})
        first["slideProperties"]["notesPage"]["pageElements"][1]["shape"]["text"]["textElements"].append({"futureText": {}})
        deck = normalize_presentation(self.payload, fetched_at=NOW)
        self.assertEqual(deck.slides[0].elements[1].extraction_status, "partial")
        self.assertEqual(deck.slides[0].speaker_notes.status, "unavailable")
        self.assertEqual(deck.slides[0].speaker_notes.text, "Presenter-authored explanation.\n")
        self.assertEqual(sum(i.code == "unsupported_text" for i in deck.issues), 2)

    def test_whitespace_notes_and_missing_notes_reference_are_distinct(self):
        page = self.payload["slides"][0]["slideProperties"]["notesPage"]
        page["pageElements"][1]["shape"]["text"]["textElements"] = [{"textRun": {"content": "\n"}}]
        notes = normalize_presentation(self.payload, fetched_at=NOW).slides[0].speaker_notes
        self.assertEqual((notes.status, notes.text), ("empty", "\n"))
        page.pop("notesProperties")
        notes = normalize_presentation(self.payload, fetched_at=NOW).slides[0].speaker_notes
        self.assertEqual(notes.status, "unavailable")

    def test_table_holes_overlaps_and_multiple_variants_are_rejected(self):
        for change in ("hole", "overlap", "variants", "huge", "missing_rows"):
            payload = copy.deepcopy(self.payload)
            element = payload["slides"][0]["pageElements"][2]
            table = element["table"]
            if change == "hole":
                table["tableRows"][0]["tableCells"].pop()
            elif change == "overlap":
                table["tableRows"][0]["tableCells"][1]["location"]["columnIndex"] = 0
            elif change == "variants":
                element["shape"] = {}
            elif change == "huge":
                table["rows"] = 100001
            else:
                table["tableRows"] = []
            with self.subTest(change=change), self.assertRaises(PresentationSourceError):
                normalize_presentation(payload, fetched_at=NOW)

    def test_malformed_payloads_fail_instead_of_silently_losing_content(self):
        cases = [None, [], {}, {"presentationId": "x", "slides": "bad"},
                 {"presentationId": "x", "slides": [{"pageElements": []}]},
                 {"presentationId": "x", "slides": [{"objectId": "s"}, {"objectId": "s"}]},
                 {"presentationId": "x", "revisionId": 42}]
        bad_text = copy.deepcopy(self.payload)
        bad_text["slides"][0]["pageElements"][0]["shape"]["text"]["textElements"][1]["textRun"]["content"] = 9
        cases.append(bad_text)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(PresentationSourceError) as ctx:
                normalize_presentation(payload, fetched_at=NOW)
            self.assertEqual(ctx.exception.code, "malformed_source")


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def source(self, body=None):
        opener = Mock(return_value=io.BytesIO(body if body is not None else json.dumps(self.payload).encode()))
        return GoogleSlidesSource("synthetic-test-token", open_url=opener, clock=lambda: NOW), opener

    def test_fetches_one_presentation_using_bounded_authorized_get(self):
        source, opener = self.source()
        result = source.ingest("synthetic_deck")
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "https://slides.googleapis.com/v1/presentations/synthetic_deck")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-test-token")
        self.assertEqual(opener.call_args.kwargs["timeout"], 30)
        self.assertEqual(result.source_revision.fetched_at, NOW)
        self.assertEqual(len(result.slides), 3)

    def test_rejects_missing_token_and_invalid_document_id_before_request(self):
        for token in ("", "bad\ntoken"):
            with self.assertRaises(PresentationSourceError):
                GoogleSlidesSource(token)
        source, opener = self.source()
        with self.assertRaises(PresentationSourceError):
            source.ingest("https://untrusted.example/secret")
        opener.assert_not_called()

    def test_http_network_and_invalid_responses_are_sanitized(self):
        for error, code in ((HTTPError("url", 401, "secret", {}, None), "authentication"),
                            (HTTPError("url", 403, "secret", {}, None), "access"),
                            (HTTPError("url", 404, "secret", {}, None), "access"),
                            (HTTPError("url", 429, "secret", {}, None), "transport"),
                            (URLError("secret"), "transport"), (TimeoutError("secret"), "transport")):
            source, opener = self.source()
            opener.side_effect = error
            with self.subTest(code=code), self.assertRaises(PresentationSourceError) as ctx:
                source.ingest("synthetic_deck")
            self.assertEqual(ctx.exception.code, code)
            self.assertNotIn("secret", str(ctx.exception))
        for body in (b"not json", b"\xff", b"[]", b'{"presentationId":"wrong"}'):
            source, _ = self.source(body)
            with self.assertRaises(PresentationSourceError):
                source.ingest("synthetic_deck")

    def test_interrupted_body_is_a_sanitized_transport_failure(self):
        source, opener = self.source()
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.side_effect = IncompleteRead(b"private source content", 100)
        opener.return_value = response
        with self.assertRaises(PresentationSourceError) as ctx:
            source.ingest("synthetic_deck")
        self.assertEqual(ctx.exception.code, "transport")
        self.assertNotIn("private source", str(ctx.exception))

    def test_oversized_body_and_redirect_are_refused(self):
        source, opener = self.source(b"12345")
        with patch("presentation.adapters.google_slides.MAX_RESPONSE_BYTES", 4):
            with self.assertRaises(PresentationSourceError):
                source.ingest("synthetic_deck")
        request = opener.call_args.args[0]
        with self.assertRaises(HTTPError) as ctx:
            _NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://untrusted.example")
        ctx.exception.close()

    def test_cli_writes_normalized_json_without_printing_content_or_token(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deck.json"
            stdout, stderr = io.StringIO(), io.StringIO()
            source, _ = self.source()
            with patch("experiments.ingest_google_slides.GoogleSlidesSource", return_value=source), \
                 patch.dict("os.environ", {"GOOGLE_SLIDES_ACCESS_TOKEN": "synthetic-test-token"}), \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(["synthetic_deck", "--output", str(output)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.read_text())["schema_version"], "1.0")
            self.assertNotIn("Presenter-authored", stdout.getvalue() + stderr.getvalue())
            self.assertNotIn("synthetic-test-token", stdout.getvalue() + stderr.getvalue())
            # Existing output is protected from accidental overwrite.
            with patch.dict("os.environ", {"GOOGLE_SLIDES_ACCESS_TOKEN": "synthetic-test-token"}), \
                 patch("experiments.ingest_google_slides.GoogleSlidesSource", return_value=source), \
                 redirect_stderr(stderr):
                self.assertEqual(main(["synthetic_deck", "--output", str(output)]), 1)

    def test_cli_missing_token_fails_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            output = Path(directory) / "deck.json"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["synthetic_deck", "--output", str(output)]), 1)
            self.assertFalse(output.exists())

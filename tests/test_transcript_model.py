"""Internal transcript schema and canonical serialization guarantees."""
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

from transcription.model import (
    Provenance, SegmentUpdated, StreamEnded, StreamStarted, StreamStatusChanged,
    TranscriptEvent, TranscriptValidationError, event_from_json, event_to_json,
)


def event(initial_payload, sequence=0, observed_at_ms=0, **changes):
    values = dict(schema_version="1.0", session_id="session-a", stream_id="stream-a",
                  sequence=sequence, observed_at_ms=observed_at_ms,
                  provenance=Provenance("synthetic", "replay", "fixture-a", None),
                  payload=initial_payload)
    values.update(changes)
    return TranscriptEvent(**values)


def segment(**changes):
    values = dict(segment_id="s0", segment_index=0, revision=1, status="partial",
                  text="Attention helps", start_ms=0, end_ms=100, speaker_id=None)
    values.update(changes)
    return SegmentUpdated(**values)


class TranscriptModelTests(unittest.TestCase):
    def test_all_payloads_round_trip_and_preserve_exact_unicode_text(self):
        for payload in (StreamStarted(), segment(text="  世界\n"),
                        StreamStatusChanged("missing"), StreamEnded("completed")):
            original = event(payload, observed_at_ms=100)
            encoded = event_to_json(original)
            with self.subTest(payload=payload.kind):
                self.assertEqual(event_from_json(encoded), original)
                self.assertEqual(event_to_json(event_from_json(encoded)), encoded)

    def test_aware_timestamps_use_one_utc_rfc3339_representation(self):
        instant = datetime(2026, 9, 25, 20, 30, 1, 123456, timezone.utc)
        shifted = instant.astimezone(timezone(timedelta(hours=-4)))
        a = event_to_json(event(StreamStarted(instant)))
        b = event_to_json(event(StreamStarted(shifted)))
        self.assertEqual(a, b)
        self.assertEqual(json.loads(a)["payload"]["started_at"],
                         "2026-09-25T20:30:01.123456Z")
        self.assertEqual(event_from_json(a).payload.started_at.tzinfo, timezone.utc)
        self.assertIn("00.000000Z", event_to_json(event(StreamStarted(
            datetime(2026, 9, 25, tzinfo=timezone.utc)))))

    def test_naive_datetime_is_rejected_at_construction_and_decode(self):
        with self.assertRaises(TranscriptValidationError):
            StreamStarted(datetime(2026, 9, 25))
        doc = json.loads(event_to_json(event(StreamStarted())))
        for timestamp in ("2026-09-25T00:00:00", "private-invalid-value", 123):
            doc["payload"]["started_at"] = timestamp
            with self.subTest(timestamp=timestamp), self.assertRaises(TranscriptValidationError):
                event_from_json(json.dumps(doc))

    def test_offset_json_timestamp_is_canonicalized(self):
        doc = json.loads(event_to_json(event(StreamStarted())))
        doc["payload"]["started_at"] = "2026-09-25T16:30:00-04:00"
        self.assertIn("2026-09-25T20:30:00.000000Z", event_to_json(
            event_from_json(json.dumps(doc))))

    def test_envelope_and_provenance_validation(self):
        bad = ({"schema_version": "2"}, {"session_id": " "}, {"stream_id": 1},
               {"sequence": True}, {"sequence": -1}, {"observed_at_ms": 0.5},
               {"observed_at_ms": -1}, {"payload": {}}, {"provenance": {}},
               {"provenance": Provenance("other", "replay", "x", None)},
               {"provenance": Provenance("synthetic", "other", "x", None)},
               {"provenance": Provenance("synthetic", "replay", "", None)},
               {"provenance": Provenance("synthetic", "replay", "x", "")})
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(TranscriptValidationError):
                event(StreamStarted(), **changes)

    def test_segment_validation_including_bool_counters_and_unknown_offsets(self):
        bad = ({"segment_id": ""}, {"segment_index": -1}, {"segment_index": True},
               {"revision": 0}, {"revision": True}, {"status": "guessed"},
               {"text": None}, {"speaker_id": ""}, {"start_ms": None},
               {"end_ms": None}, {"start_ms": -1}, {"start_ms": True},
               {"start_ms": 101}, {"end_ms": 201}, {"end_ms": 1.5})
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(TranscriptValidationError):
                event(segment(**changes), sequence=1, observed_at_ms=200)
        self.assertEqual(event(segment(text="", start_ms=None, end_ms=None),
                               observed_at_ms=0).payload.text, "")

    def test_invalid_status_end_reason_and_payload_kind(self):
        for payload in (StreamStatusChanged("unknown"), StreamEnded("unknown")):
            with self.assertRaises(TranscriptValidationError):
                event(payload)
        doc = json.loads(event_to_json(event(StreamStarted())))
        doc["payload"]["kind"] = "private-unknown-kind"
        with self.assertRaises(TranscriptValidationError) as caught:
            event_from_json(json.dumps(doc))
        self.assertNotIn("private", str(caught.exception))

    def test_decode_rejects_malformed_missing_extra_and_duplicate_fields(self):
        good = json.loads(event_to_json(event(StreamStarted())))
        cases = ["{private", "[]", "null", '{"sequence": 0, "sequence": 1}',
                 json.dumps({**good, "extra": "private"})]
        for key in ("session_id", "provenance", "payload"):
            cases.append(json.dumps({k: v for k, v in good.items() if k != key}))
        for key, value in (("provenance", []), ("payload", None),
                           ("payload", {"kind": "stream_started"}),
                           ("provenance", {**good["provenance"], "extra": 1})):
            cases.append(json.dumps({**good, key: value}))
        cases.append(json.dumps({**good, "sequence": float("nan")}))
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(TranscriptValidationError) as caught:
                event_from_json(raw)
            self.assertNotIn("private", str(caught.exception))

    def test_event_and_payload_are_immutable(self):
        original = event(StreamStarted())
        with self.assertRaises(FrozenInstanceError):
            original.sequence = 5
        with self.assertRaises(FrozenInstanceError):
            original.payload.started_at = None
        with self.assertRaises(TranscriptValidationError):
            replace(original, sequence=-1)

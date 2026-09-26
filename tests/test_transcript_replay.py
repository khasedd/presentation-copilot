"""Fixture-to-state journeys, revision safety, and stream boundaries."""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from transcription.model import (
    Provenance, StreamEnded, StreamStarted, StreamStatusChanged,
    TranscriptValidationError, event_to_json,
)
from transcription.replay import load_replay, replay
from transcription.stream import TranscriptAccumulator
from test_transcript_model import event, segment

FIXTURE = Path(__file__).parent / "fixtures/transcript_evolution.json"


class TranscriptStreamTests(unittest.TestCase):
    def setUp(self):
        self.stream = TranscriptAccumulator()
        self.stream.apply(event(StreamStarted()))

    def assert_rejected_unchanged(self, candidate):
        before = self.stream.state
        with self.assertRaises(TranscriptValidationError):
            self.stream.apply(candidate)
        self.assertIs(self.stream.state, before)

    def test_partial_corrected_final_and_post_final_correction_replace_text(self):
        states = []
        for revision, status, text in ((1, "partial", "Our late city"),
                                       (2, "partial", "Our latency"),
                                       (3, "final", "Our latency is low."),
                                       (4, "final", "Our latency is lower.")):
            states.append(self.stream.apply(event(segment(
                revision=revision, status=status, text=text), revision, 100)))
        self.assertEqual(len(states[-1].segments), 1)
        self.assertEqual(states[-1].segments[0].text, "Our latency is lower.")
        self.assertEqual(states[0].segments[0].text, "Our late city")
        self.assertEqual(states[-1].segments[0].revision, 4)

    def test_interleaved_revisions_preserve_first_observed_segment_order(self):
        self.stream.apply(event(segment(), 1, 100))
        self.stream.apply(event(segment(segment_id="s1", segment_index=1,
                                        start_ms=0, end_ms=50), 2, 100))
        result = self.stream.apply(event(segment(revision=2, status="final",
                                                 start_ms=10, speaker_id="speaker-b"), 3, 100))
        self.assertEqual([s.segment_id for s in result.segments], ["s0", "s1"])
        self.assertEqual(result.segments[0].speaker_id, "speaker-b")
        self.assertEqual(result.segments[0].start_ms, 10)

    def test_duplicate_gap_old_sequence_and_regressing_time_are_atomic(self):
        self.stream.apply(event(segment(), 1, 100))
        for seq, timestamp in ((1, 100), (0, 100), (3, 100), (2, 99)):
            self.assert_rejected_unchanged(event(StreamStatusChanged("delayed"), seq, timestamp))
        self.assertEqual(self.stream.apply(event(segment(revision=2), 2, 100)).sequence, 2)

    def test_wrong_session_stream_or_provenance_is_atomic(self):
        for changes in ({"session_id": "other"}, {"stream_id": "other"},
                        {"provenance": Provenance("synthetic", "replay", "other", None)},
                        {"provenance": Provenance("synthetic", "live", "fixture-a", None)}):
            self.assert_rejected_unchanged(event(segment(), 1, 100, **changes))

    def test_revision_gaps_stale_revisions_and_index_changes_are_rejected(self):
        self.stream.apply(event(segment(), 1, 100))
        for changes in ({"revision": 1}, {"revision": 3},
                        {"revision": 2, "segment_index": 1},
                        {"segment_id": "s1", "segment_index": 2},
                        {"segment_id": "s1", "segment_index": 1, "revision": 2}):
            self.assert_rejected_unchanged(event(segment(**changes), 2, 100))

    def test_first_result_can_be_final_but_cannot_revert_to_partial(self):
        self.stream.apply(event(segment(status="final"), 1, 100))
        self.assert_rejected_unchanged(event(segment(revision=2), 2, 100))
        state = self.stream.apply(event(segment(revision=2, status="final", text=""), 2, 100))
        self.assertEqual(state.segments[0].text, "")

    def test_start_requirements_and_no_repeated_start(self):
        for first in (event(segment(), 0, 100), event(StreamEnded("completed")),
                      event(StreamStarted(), 1), event(StreamStarted(), 0, 1)):
            empty = TranscriptAccumulator()
            with self.assertRaises(TranscriptValidationError):
                empty.apply(first)
            self.assertIsNone(empty.state)
        self.assert_rejected_unchanged(event(StreamStarted(), 1))

    def test_degraded_recovery_keeps_segments_and_history(self):
        self.stream.apply(event(segment(), 1, 100))
        for sequence, status in enumerate(("delayed", "missing", "ready"), 2):
            state = self.stream.apply(event(StreamStatusChanged(status), sequence, 100))
        self.assertEqual(state.status, "ready")
        self.assertEqual(state.segments[0].status, "partial")
        self.assertEqual([e.payload.status for e in state.status_history],
                         ["delayed", "missing", "ready"])

    def test_failure_only_allows_failed_closure(self):
        self.stream.apply(event(StreamStatusChanged("failed"), 1))
        for payload in (StreamStatusChanged("ready"), StreamEnded("completed"),
                        StreamEnded("cancelled"), segment()):
            self.assert_rejected_unchanged(event(payload, 2, 100))
        state = self.stream.apply(event(StreamEnded("failed"), 2, 100))
        self.assertEqual((state.status, state.end_reason), ("failed", "failed"))

    def test_end_preserves_partial_and_rejects_all_later_input(self):
        self.stream.apply(event(segment(), 1, 100))
        state = self.stream.apply(event(StreamEnded("completed"), 2, 100))
        self.assertEqual(state.segments[0].status, "partial")
        self.assertEqual(state.end_reason, "completed")
        for payload in (StreamStarted(), StreamEnded("completed"), segment(revision=2)):
            self.assert_rejected_unchanged(event(payload, 3, 100))

    def test_segments_do_not_implicitly_recover_missing_status(self):
        self.stream.apply(event(StreamStatusChanged("missing"), 1, 100))
        state = self.stream.apply(event(segment(start_ms=None, end_ms=None), 2, 100))
        self.assertEqual(state.status, "missing")
        ended = self.stream.apply(event(StreamEnded("completed"), 3, 100))
        self.assertEqual(ended.status, "missing")
        self.assertEqual(ended.segments[0].status, "partial")

    def test_invalid_object_cannot_mutate_state(self):
        self.assert_rejected_unchanged({"payload": "private"})

    def test_direct_failure_and_cancelled_empty_stream(self):
        for reason in ("failed", "cancelled"):
            stream = TranscriptAccumulator()
            stream.apply(event(StreamStarted()))
            state = stream.apply(event(StreamEnded(reason), 1))
            self.assertEqual(state.end_reason, reason)
            self.assertEqual(state.status, "failed" if reason == "failed" else "ready")

    def test_reconnection_and_new_session_use_fresh_state(self):
        old = event(segment(), 1, 100)
        self.stream.apply(old)
        for session in ("session-a", "session-b"):
            stream = TranscriptAccumulator()
            state = stream.apply(event(StreamStarted(), session_id=session, stream_id="stream-b"))
            self.assertEqual(state.segments, ())
            with self.assertRaises(TranscriptValidationError):
                stream.apply(old)
            stream.apply(event(segment(), 1, 100, session_id=session, stream_id="stream-b"))


class ReplayTests(unittest.TestCase):
    def test_fixture_replays_identically_without_time_or_network(self):
        with patch("time.sleep", side_effect=AssertionError("sleep")), \
             patch("time.time", side_effect=AssertionError("wall clock")), \
             patch("socket.socket", side_effect=AssertionError("network")):
            first = tuple(replay(load_replay(FIXTURE)))
            second = tuple(replay(load_replay(FIXTURE)))
        self.assertEqual(first, second)
        self.assertEqual(first[1].segments[0].text, "Our late city")
        self.assertEqual(first[2].segments[0].text, "Our latency")
        self.assertEqual(first[-1].segments[0].text, "Our latency is twenty milliseconds.")
        self.assertEqual(first[-1].segments[0].revision, 4)
        self.assertEqual(first[-1].segments[1].status, "partial")
        self.assertEqual(first[-1].end_reason, "completed")
        self.assertTrue(all(s.provenance.delivery == "replay" for s in first))

    def test_live_recording_gets_replay_delivery_without_mutating_origin(self):
        provenance = Provenance("transcriber", "live", "recording-a", "synthetic-provider-label")
        events = [event(StreamStarted(), provenance=provenance),
                  event(StreamEnded("completed"), 1, provenance=provenance)]
        state = tuple(replay(events))[-1]
        self.assertEqual(state.provenance, replace(provenance, delivery="replay"))
        self.assertEqual(events[0].provenance.delivery, "live")
        self.assertEqual(state.session_id, events[0].session_id)

    def test_empty_and_truncated_replay_fail_without_inventing_completion(self):
        for events in ([], [event(StreamStarted())],
                       [event(StreamStarted()), event(segment(), 1, 100)]):
            with self.subTest(events=events), self.assertRaises(TranscriptValidationError) as caught:
                tuple(replay(events))
            self.assertEqual(caught.exception.code, "incomplete_stream")

    def test_fixture_order_is_never_sorted_or_repaired(self):
        events = list(load_replay(FIXTURE))
        events[1], events[2] = events[2], events[1]
        with self.assertRaises(TranscriptValidationError):
            tuple(replay(events))

    def test_replay_failure_boundary_and_trailing_event(self):
        events = [event(StreamStarted()), event(StreamStatusChanged("failed"), 1),
                  event(StreamEnded("failed"), 2)]
        self.assertEqual(tuple(replay(events))[-1].end_reason, "failed")
        with self.assertRaises(TranscriptValidationError):
            tuple(replay(events + [event(StreamStatusChanged("ready"), 3)]))

    def test_loader_rejects_non_utf8_and_propagates_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            with self.assertRaises(FileNotFoundError):
                tuple(load_replay(path))
            path.write_bytes(b"\xffprivate")
            with self.assertRaises(TranscriptValidationError) as caught:
                tuple(load_replay(path))
            self.assertNotIn("private", str(caught.exception))

    def test_loader_rejects_invalid_json_shape_and_event_without_content_in_error(self):
        for raw in ("private{", "{}", "[null]", "[NaN]", '[{"x":1,"x":2}]'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fixture.json"
                path.write_text(raw)
                with self.assertRaises(TranscriptValidationError) as caught:
                    tuple(load_replay(path))
                self.assertNotIn("private", str(caught.exception))

    def test_loader_preserves_live_origin_and_marks_delivery_as_replay(self):
        original = event(StreamStarted(), provenance=Provenance(
            "transcriber", "live", "recording", None))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text("[" + event_to_json(original) + "]")
            loaded = tuple(load_replay(path))
        self.assertEqual(loaded[0].provenance.origin, "transcriber")
        self.assertEqual(loaded[0].provenance.delivery, "replay")

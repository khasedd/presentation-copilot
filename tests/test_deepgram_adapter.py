"""Deterministic Deepgram-message normalization tests; no network or audio."""
from datetime import datetime, timezone
import unittest

from transcription.adapters.deepgram import DeepgramAdapter, DeepgramAdapterError
from transcription.model import SegmentUpdated, TranscriptValidationError


STARTED_AT = datetime(2026, 9, 27, 18, 0, tzinfo=timezone.utc)


def word(text, start, end):
    return {"word": text, "punctuated_word": text, "start": start, "end": end}


def result(text, start, duration, *, final=False, words=None):
    return {
        "type": "Results",
        "start": start,
        "duration": duration,
        "is_final": final,
        "speech_final": final,
        "channel": {"alternatives": [{"transcript": text, "words": words or []}]},
    }


class DeepgramAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = DeepgramAdapter(
            session_id="session-a",
            source_id="internal-mic",
            started_at=STARTED_AT,
            stream_id="stream-a",
        )

    def test_initial_revised_and_final_results_use_adapter_owned_counters(self):
        first = self.adapter.accept(result(
            "Our late city", 0, 0.9,
            words=[word("Our", 0, 0.2), word("late", 0.2, 0.5),
                   word("city", 0.5, 0.9)]), observed_at_ms=1000)
        second = self.adapter.accept(result(
            "Our latency", 0, 1.1,
            words=[word("Our", 0, 0.2), word("latency", 0.2, 1.1)]),
            observed_at_ms=1200)
        third = self.adapter.accept(result(
            "Our latency.", 0, 1.1, final=True,
            words=[word("Our", 0, 0.2), word("latency.", 0.2, 1.1)]),
            observed_at_ms=1400)

        updates = [first[0].payload, second[0].payload, third[0].payload]
        self.assertTrue(all(isinstance(item, SegmentUpdated) for item in updates))
        self.assertEqual([event.sequence for event in first + second + third], [1, 2, 3])
        self.assertEqual([item.revision for item in updates], [1, 2, 3])
        self.assertEqual([item.status for item in updates], ["partial", "partial", "final"])
        self.assertEqual({item.segment_id for item in updates}, {"stream-a:segment:0"})
        self.assertEqual({item.segment_index for item in updates}, {0})
        self.assertEqual((updates[-1].start_ms, updates[-1].end_ms), (0, 1100))
        self.assertEqual(self.adapter.accumulator.state.segments, (updates[-1],))

    def test_shorter_final_finalizes_settled_span_and_opens_timed_remainder(self):
        self.adapter.accept(result(
            "alpha beta gamma", 0, 3,
            words=[word("alpha", 0, 1), word("beta", 1, 2),
                   word("gamma", 2, 3)]), observed_at_ms=3100)

        emitted = self.adapter.accept(result(
            "alpha beta", 0, 2, final=True,
            words=[word("alpha", 0, 1), word("beta", 1, 2)]),
            observed_at_ms=3200)

        self.assertEqual([event.sequence for event in emitted], [2, 3])
        settled, remainder = (event.payload for event in emitted)
        self.assertEqual((settled.segment_id, settled.segment_index, settled.revision),
                         ("stream-a:segment:0", 0, 2))
        self.assertEqual((settled.status, settled.text, settled.start_ms, settled.end_ms),
                         ("final", "alpha beta", 0, 2000))
        self.assertEqual((remainder.segment_id, remainder.segment_index, remainder.revision),
                         ("stream-a:segment:1", 1, 1))
        self.assertEqual((remainder.status, remainder.text,
                          remainder.start_ms, remainder.end_ms),
                         ("partial", "gamma", 2000, 3000))

        revision = self.adapter.accept(result(
            "gamma delta", 2, 2,
            words=[word("gamma", 2, 3), word("delta", 3, 4)]),
            observed_at_ms=4100)[0].payload
        self.assertEqual((revision.segment_id, revision.segment_index, revision.revision),
                         (remainder.segment_id, 1, 2))
        self.assertEqual([segment.status for segment in self.adapter.accumulator.state.segments],
                         ["final", "partial"])

    def test_shorter_final_clips_tentative_word_crossing_final_boundary(self):
        self.adapter.accept(result(
            "alpha beta gamma", 0, 3,
            words=[word("alpha", 0, 1), word("beta", 1, 2.1),
                   word("gamma", 2.1, 3)]), observed_at_ms=3100)

        emitted = self.adapter.accept(result(
            "alpha", 0, 2, final=True,
            words=[word("alpha", 0, 1)]), observed_at_ms=3200)

        settled, remainder = (event.payload for event in emitted)
        self.assertEqual((settled.status, settled.text, settled.end_ms),
                         ("final", "alpha", 2000))
        self.assertEqual((remainder.status, remainder.text,
                          remainder.start_ms, remainder.end_ms),
                         ("partial", "beta gamma", 2000, 3000))

        revision = self.adapter.accept(result(
            "beta gamma revised", 2, 2,
            words=[word("beta", 2, 2.4), word("gamma", 2.4, 3),
                   word("revised", 3, 4)]), observed_at_ms=4100)[0].payload
        self.assertEqual((revision.segment_id, revision.revision),
                         (remainder.segment_id, 2))

    def test_provider_timestamps_round_to_milliseconds(self):
        update = self.adapter.accept(result(
            "timed", 0.1254, 0.7504,
            words=[word("timed", 0.1254, 0.8758)]),
            observed_at_ms=1000)[0].payload
        self.assertEqual((update.start_ms, update.end_ms), (125, 876))

    def test_word_timing_overlap_does_not_invalidate_result_range(self):
        update = self.adapter.accept(result(
            "alpha beta", 0, 1,
            words=[word("alpha", 0, 0.6), word("beta", 0.55, 1)]),
            observed_at_ms=1100)[0].payload
        self.assertEqual((update.text, update.start_ms, update.end_ms),
                         ("alpha beta", 0, 1000))

    def test_one_millisecond_word_boundary_drift_is_clipped(self):
        update = self.adapter.accept(result(
            "timed", 1, 1,
            words=[word("timed", 0.9994, 2.0006)]),
            observed_at_ms=2100)[0].payload
        self.assertEqual((update.start_ms, update.end_ms), (1000, 2000))

    def test_empty_punctuated_word_falls_back_to_raw_word_for_remainder(self):
        first = word("alpha", 0, 1)
        second = word("beta", 1, 2)
        second["punctuated_word"] = ""
        self.adapter.accept(result(
            "alpha beta", 0, 2, words=[first, second]),
            observed_at_ms=2100)

        emitted = self.adapter.accept(result(
            "alpha", 0, 1, final=True, words=[first]),
            observed_at_ms=2200)
        self.assertEqual(emitted[1].payload.text, "beta")

    def test_optional_word_metadata_variance_cannot_abort_valid_result(self):
        noisy_words = [
            word("alpha", -0.02, 1),
            {"word": "missing timing", "start": None, "end": 1.5},
            "not a word object",
            word("gamma", 2.9, 3.05),
        ]
        first = self.adapter.accept(result(
            "alpha beta gamma", 0, 3, words=noisy_words),
            observed_at_ms=3100)
        self.assertEqual(first[0].payload.text, "alpha beta gamma")

        emitted = self.adapter.accept(result(
            "alpha beta", 0, 2, final=True,
            words=[word("alpha", 0, 1), word("beta", 1, 2)]),
            observed_at_ms=3200)
        self.assertEqual(len(emitted), 2)
        self.assertEqual(emitted[1].payload.text, "gamma")
        self.assertEqual(
            (emitted[1].payload.start_ms, emitted[1].payload.end_ms),
            (2000, 3000),
        )

        replacement = DeepgramAdapter(
            session_id="session-a",
            source_id="internal-mic",
            started_at=STARTED_AT,
            stream_id="stream-b",
        )
        message = result("valid result text", 0, 1)
        message["channel"]["alternatives"][0]["words"] = None
        update = replacement.accept(message, observed_at_ms=1100)[0].payload
        self.assertEqual(update.text, "valid result text")

    def test_required_result_shape_has_content_free_reason_codes(self):
        cases = (
            (result("private transcript", -1, 1), "invalid_result_timing"),
            (result("private transcript", 0, True), "invalid_result_timing"),
            ({"type": "Results", "start": 0, "duration": 1,
              "is_final": False, "channel": {}}, "invalid_result_alternatives"),
        )
        for message, expected_code in cases:
            with self.subTest(expected_code=expected_code), \
                    self.assertRaises(DeepgramAdapterError) as caught:
                self.adapter.accept(message, observed_at_ms=2000)
            self.assertEqual(caught.exception.code, expected_code)
            self.assertNotIn("private", str(caught.exception))

    def test_empty_and_non_result_messages_are_no_ops(self):
        messages = [
            {"type": "Metadata", "request_id": "sanitized"},
            {"type": "SpeechStarted", "timestamp": 0.1},
            {"type": "UtteranceEnd", "last_word_end": 0.2},
            result("", 0, 0.2, words=[]),
        ]
        for message in messages:
            self.assertEqual(self.adapter.accept(message, observed_at_ms=300), ())
        self.assertEqual(self.adapter.accumulator.state.sequence, 0)
        self.assertEqual(self.adapter.accumulator.state.segments, ())

    def test_malformed_or_unexpected_input_is_sanitized_and_atomic(self):
        malformed = [
            "private transcript",
            {},
            {"type": "Unknown", "private": "transcript"},
            {"type": "Results", "start": 0, "duration": 1,
             "is_final": False, "channel": {}},
            result("private transcript", -1, 1),
            result("private transcript", 0, True),
        ]
        for message in malformed:
            before = self.adapter.accumulator.state
            with self.subTest(message=type(message).__name__), \
                 self.assertRaises(DeepgramAdapterError) as caught:
                self.adapter.accept(message, observed_at_ms=2000)
            self.assertNotIn("private", str(caught.exception))
            self.assertIs(self.adapter.accumulator.state, before)

    def test_failure_emits_explicit_status_and_failed_closure(self):
        emitted = self.adapter.fail(observed_at_ms=250, code="socket_closed")
        self.assertEqual([event.sequence for event in emitted], [1, 2])
        self.assertEqual(emitted[0].payload.status, "failed")
        self.assertEqual(emitted[1].payload.reason, "failed")
        self.assertEqual(self.adapter.accumulator.state.status, "failed")
        self.assertEqual(self.adapter.accumulator.state.end_reason, "failed")

    def test_reconnect_uses_fresh_stream_and_rejects_old_stream_events(self):
        old_update = self.adapter.accept(result("old", 0, 0.5), observed_at_ms=600)[0]
        self.adapter.fail(observed_at_ms=700, code="intentional_disconnect")

        replacement = self.adapter.reconnect(started_at=STARTED_AT)
        self.assertNotEqual(replacement.stream_id, self.adapter.stream_id)
        self.assertEqual(replacement.accumulator.state.sequence, 0)
        self.assertEqual(replacement.accumulator.state.segments, ())
        with self.assertRaises(TranscriptValidationError):
            replacement.accumulator.apply(old_update)

    def test_final_segment_cannot_return_to_partial(self):
        self.adapter.accept(result("settled", 0, 1, final=True), observed_at_ms=1100)
        before = self.adapter.accumulator.state
        with self.assertRaises(DeepgramAdapterError):
            self.adapter.accept(result("tentative", 0, 1.2), observed_at_ms=1300)
        self.assertIs(self.adapter.accumulator.state, before)

    def test_shorter_final_without_timed_remainder_is_blocking_incompatibility(self):
        self.adapter.accept(result("alpha beta gamma", 0, 3), observed_at_ms=3100)
        with self.assertRaises(DeepgramAdapterError) as caught:
            self.adapter.accept(result("alpha beta", 0, 2, final=True),
                                observed_at_ms=3200)
        self.assertEqual(caught.exception.code, "shorter_final_incompatible")
        self.assertEqual(self.adapter.accumulator.state.sequence, 1)

    def test_shorter_final_with_all_timed_words_inside_span_is_one_revision(self):
        self.adapter.accept(result(
            "today I am demonstrating the live technical assistant", 0, 4,
            words=[
                word("today", 0, 0.4),
                word("I", 0.4, 0.6),
                word("am", 0.6, 0.8),
                word("demonstrating", 0.8, 1.5),
                word("the", 1.5, 1.7),
                word("live", 1.7, 2.1),
                word("technical", 2.1, 2.7),
                word("assistant", 2.7, 3.9),
            ]), observed_at_ms=4100)

        emitted = self.adapter.accept(result(
            "today I demonstrated the assistant", 0, 3.92, final=True,
            words=[
                word("today", 0, 0.4),
                word("I", 0.4, 0.6),
                word("demonstrated", 0.6, 1.5),
                word("the", 1.5, 1.7),
                word("assistant", 1.7, 3.9),
            ]), observed_at_ms=4200)

        self.assertEqual(len(emitted), 1)
        update = emitted[0].payload
        self.assertEqual((update.segment_index, update.revision, update.status),
                         (0, 2, "final"))
        self.assertEqual((update.start_ms, update.end_ms), (0, 3920))
        self.assertEqual(self.adapter.accumulator.state.segments, (update,))

    def test_observation_offsets_and_close_counters_are_consecutive(self):
        self.adapter.accept(result("one", 0, 0.1), observed_at_ms=150)
        self.adapter.accept(result("one", 0, 0.1, final=True), observed_at_ms=180)
        ended = self.adapter.close(observed_at_ms=200)
        self.assertEqual(ended.sequence, 3)
        self.assertEqual(ended.payload.reason, "completed")
        self.assertEqual(self.adapter.accumulator.state.end_reason, "completed")


if __name__ == "__main__":
    unittest.main()

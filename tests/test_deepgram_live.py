"""Offline tests for the bounded Deepgram microphone experiment harness."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from experiments.deepgram_live import (
    ListenConfig,
    _StreamEvidence,
    _update_evidence,
    audio_cursor_ms,
    build_listen_url,
    capture_command,
    load_deepgram_key,
    main,
    safe_trial_report,
    technical_term_recall,
    word_error_rate,
)
from transcription.adapters.deepgram import DeepgramAdapter


class DeepgramLiveConfigurationTests(unittest.TestCase):
    def test_listen_url_has_required_privacy_audio_and_latency_settings(self):
        config = ListenConfig()
        parsed = urlparse(build_listen_url(config))
        query = parse_qs(parsed.query)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                         ("wss", "api.deepgram.com", "/v1/listen"))
        self.assertEqual(query, {
            "channels": ["1"],
            "encoding": ["linear16"],
            "endpointing": ["500"],
            "interim_results": ["true"],
            "language": ["en-US"],
            "mip_opt_out": ["true"],
            "model": ["nova-3"],
            "punctuate": ["true"],
            "sample_rate": ["16000"],
            "smart_format": ["true"],
            "vad_events": ["true"],
        })
        self.assertNotIn("diarize", query)
        self.assertEqual(config.chunk_ms, 50)
        self.assertEqual(config.chunk_bytes, 1600)

    def test_key_loader_prefers_environment_and_never_executes_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            marker = Path(directory) / "executed"
            path.write_text(
                "DEEPGRAM_API_KEY=file-key\n"
                f"MALICIOUS=$(touch {marker})\n",
                encoding="utf-8",
            )
            self.assertEqual(load_deepgram_key({}, path), "file-key")
            self.assertEqual(load_deepgram_key(
                {"DEEPGRAM_API_KEY": "environment-key"}, path),
                "environment-key")
            self.assertFalse(marker.exists())

    def test_capture_requests_pipewire_conversion_to_transmitted_format(self):
        config = ListenConfig()
        command = capture_command("alsa_input.example", config)
        self.assertEqual(command[0], "parec")
        self.assertIn("--device=alsa_input.example", command)
        self.assertIn("--raw", command)
        self.assertIn("--format=s16le", command)
        self.assertIn("--rate=16000", command)
        self.assertIn("--channels=1", command)
        self.assertNotIn("--file-format", command)
        self.assertEqual(audio_cursor_ms(32000, config), 1000)


class DeepgramLiveMeasurementTests(unittest.TestCase):
    def test_empty_result_does_not_create_latency_or_endpoint_samples(self):
        adapter = DeepgramAdapter(
            session_id="session",
            source_id="microphone",
            started_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
            stream_id="stream",
        )
        evidence = _StreamEvidence(stream_id="stream", adapter=adapter)
        message = {
            "type": "Results",
            "start": 0,
            "duration": 0.5,
            "is_final": True,
            "speech_final": True,
            "channel": {"alternatives": [{"transcript": "", "words": []}]},
        }
        events = adapter.accept(message, observed_at_ms=600)
        _update_evidence(evidence, message, events, 100.0)
        self.assertEqual(events, ())
        self.assertEqual(evidence.endpoint_events, 0)
        self.assertEqual(evidence.final_lags_ms, [])

    def test_word_error_rate_and_technical_term_recall_are_deterministic(self):
        reference = "Deepgram Nova three uses PipeWire and a WebSocket."
        hypothesis = "Deepgram Nova tree uses PipeWire and WebSocket extra."
        self.assertAlmostEqual(word_error_rate(reference, hypothesis), 3 / 8)
        recall, matched = technical_term_recall(
            hypothesis, ("Deepgram", "Nova three", "PipeWire", "WebSocket", "Nebius"))
        self.assertEqual(recall, 3 / 5)
        self.assertEqual(matched, 3)

    def test_safe_report_contains_metrics_but_no_transcript_or_credential(self):
        secret = "private-api-key"
        reference = "private reference words"
        hypothesis = "private hypothesis words"
        report = safe_trial_report(
            trial="A",
            duration_seconds=90.0,
            billable_seconds=91.2,
            wer=word_error_rate(reference, hypothesis),
            term_recall=0.9,
            matched_terms=9,
            total_terms=10,
            interim_lags_ms=(120.0, 220.0),
            final_lags_ms=(600.0, 900.0),
            partial_events=4,
            partial_revisions=2,
            final_events=2,
            shorter_finals=0,
            endpoint_events=1,
            timestamps_monotonic=True,
            disconnect_detected=False,
            reconnected=False,
            stream_ids=("stream-one",),
            selected_source="internal-mic",
            native_format="48000 Hz, 2 channels",
            network_context="local network",
        )
        encoded = json.dumps(report, sort_keys=True)
        self.assertNotIn(secret, encoded)
        self.assertNotIn(reference, encoded)
        self.assertNotIn(hypothesis, encoded)
        self.assertNotIn("transcript", encoded.lower())
        self.assertEqual(report["configuration"]["transmitted_format"],
                         "16000 Hz, mono, linear16")
        self.assertEqual(report["configuration"]["chunk_ms"], 50)
        self.assertEqual(report["configuration"]["endpointing_ms"], 500)
        self.assertEqual(report["latency_ms"]["interim"]["sample_count"], 2)
        self.assertEqual(report["latency_ms"]["final"]["p95"], 900.0)
        self.assertAlmostEqual(report["estimated_cost_usd"], 0.007296)


class DeepgramLiveCliTests(unittest.TestCase):
    def test_failed_trial_removes_reserved_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deepgram-output" / "failed.json"
            with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "local-test-key"}), \
                    patch("experiments.deepgram_live.OUTPUT_ROOT", output.parent), \
                    patch("experiments.deepgram_live.run_trial",
                          side_effect=RuntimeError("simulated failure")):
                with self.assertRaises(RuntimeError):
                    main([
                        "--trial", "A",
                        "--duration", "1",
                        "--source", "internal-mic",
                        "--output", str(output),
                    ])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

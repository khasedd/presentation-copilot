"""Offline tests for the bounded Deepgram microphone experiment harness."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

from experiments.deepgram_live import (
    ListenConfig,
    LiveExperimentError,
    _SentAudioClock,
    _StreamEvidence,
    _combine_report,
    _provider_end_ms,
    _run_stream,
    _safe_output_path,
    _update_evidence,
    audio_cursor_ms,
    build_listen_url,
    capture_command,
    load_deepgram_key,
    main,
    run_trial,
    safe_trial_report,
    technical_term_recall,
    word_error_rate,
)
from transcription.adapters.deepgram import DeepgramAdapter


STARTED_AT = datetime(2026, 9, 27, tzinfo=timezone.utc)


def result(text, start, duration, *, final=False):
    return {
        "type": "Results",
        "start": start,
        "duration": duration,
        "is_final": final,
        "speech_final": final,
        "channel": {"alternatives": [{"transcript": text, "words": [{
            "word": text,
            "punctuated_word": text,
            "start": start,
            "end": start + duration,
        }]}]},
    }


def evidence(stream_id):
    return _StreamEvidence(
        stream_id=stream_id,
        adapter=DeepgramAdapter(
            session_id="session",
            source_id="microphone",
            started_at=STARTED_AT,
            stream_id=stream_id,
        ),
    )


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
    def test_stream_transport_consumes_metadata_result_and_interrupts_safely(self):
        class FakeConnectionClosed(Exception):
            pass

        real_sleep = asyncio.sleep

        async def instant_sleep(_delay):
            await real_sleep(0)

        class FakeWebSocket:
            def __init__(self, messages):
                self.messages = list(messages)
                self.sent = []
                self.closed = []

            async def recv(self):
                await real_sleep(0)
                if not self.messages:
                    raise FakeConnectionClosed()
                return self.messages.pop(0)

            async def send(self, value):
                self.sent.append(value)

            async def close(self, **kwargs):
                self.closed.append(kwargs)

        class FakeCapture:
            def __init__(self):
                self.stdout = SimpleNamespace()
                self.returncode = None
                self.terminated = False

            def terminate(self):
                self.terminated = True

            async def wait(self):
                self.returncode = 0
                return 0

        async def exercise(messages, *, interrupt):
            websocket = FakeWebSocket(messages)
            capture = FakeCapture()
            module = ModuleType("websockets")
            exceptions = ModuleType("websockets.exceptions")
            exceptions.ConnectionClosed = FakeConnectionClosed

            async def connect(*_args, **_kwargs):
                return websocket

            module.connect = connect
            with patch.dict(sys.modules, {
                    "websockets": module,
                    "websockets.exceptions": exceptions,
            }), patch(
                "experiments.deepgram_live.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=capture),
            ), patch("experiments.deepgram_live.asyncio.sleep", new=instant_sleep):
                stream = await _run_stream(
                    key="local-test-key",
                    source="internal-mic",
                    session_id="session",
                    duration_seconds=0,
                    config=ListenConfig(),
                    started_at=STARTED_AT,
                    interrupt=interrupt,
                )
            self.assertTrue(capture.terminated)
            return stream, websocket

        completed, websocket = asyncio.run(exercise([
            json.dumps({"type": "Metadata", "duration": 0.5}),
            json.dumps({"type": "SpeechStarted", "timestamp": 0}),
            json.dumps(result("hello", 0, 0.5, final=True)),
        ], interrupt=False))
        self.assertEqual(completed.provider_duration_seconds, 0.5)
        self.assertEqual(completed.final_text, "hello")
        self.assertEqual(completed.final_events, 1)
        self.assertIn(json.dumps({"type": "Finalize"}), websocket.sent)
        self.assertIn(json.dumps({"type": "CloseStream"}), websocket.sent)

        interrupted, websocket = asyncio.run(exercise([], interrupt=True))
        self.assertTrue(interrupted.disconnect_detected)
        self.assertEqual(interrupted.adapter.accumulator.state.end_reason, "failed")
        self.assertEqual(websocket.closed[0]["code"], 1011)

    def test_sent_audio_clock_uses_first_cursor_covering_provider_result(self):
        clock = _SentAudioClock(ListenConfig())
        clock.sent(1600, 10.0)
        clock.sent(1600, 10.05)
        self.assertAlmostEqual(clock.lag_ms(40, 10.2), 200.0)
        self.assertAlmostEqual(clock.lag_ms(75, 10.2), 150.0)
        self.assertIsNone(clock.lag_ms(150, 10.2))

    def test_provider_timing_and_evidence_cover_partial_revision_and_final(self):
        stream = evidence("stream")
        first = result("hello", 0, 0.5)
        revised = result("hello world", 0, 0.8)
        final = result("hello world", 0, 0.8, final=True)
        self.assertEqual(_provider_end_ms(first), 500.0)
        with self.assertRaises(LiveExperimentError):
            _provider_end_ms({"start": False, "duration": 1})

        for observed_at_ms, message, lag_ms in (
                (600, first, 100.0),
                (900, revised, 80.0),
                (1000, final, 120.0)):
            events = stream.adapter.accept(message, observed_at_ms=observed_at_ms)
            _update_evidence(stream, message, events, lag_ms)

        self.assertEqual(stream.partial_events, 2)
        self.assertEqual(stream.partial_revisions, 1)
        self.assertEqual(stream.final_events, 1)
        self.assertEqual(stream.endpoint_events, 1)
        self.assertEqual(stream.interim_lags_ms, [100.0, 80.0])
        self.assertEqual(stream.final_lags_ms, [120.0])
        self.assertEqual(stream.final_text, "hello world")

    def test_combined_report_never_scores_across_reconnected_streams(self):
        first = evidence("stream-one")
        second = evidence("stream-two")
        first.sent_bytes = 32000
        first.disconnect_detected = True
        second.provider_duration_seconds = 1.25
        report = _combine_report(
            trial="C",
            requested_duration=2.25,
            streams=(first, second),
            source="internal-mic",
            native_format="48000 Hz, 2 channels, s16",
            network_context="local network",
            reference="private cross stream speech",
        )
        self.assertEqual(report["billable_duration_seconds"], 2.25)
        self.assertIsNone(report["accuracy"]["wer"])
        self.assertEqual(report["accuracy"]["total_terms"], 0)
        self.assertTrue(report["behavior"]["disconnect_detected"])
        self.assertTrue(report["behavior"]["reconnected"])
        self.assertEqual(report["behavior"]["stream_ids"],
                         ["stream-one", "stream-two"])

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
    def test_trial_orchestration_uses_one_stream_or_two_fresh_streams(self):
        first = evidence("stream-one")
        second = evidence("stream-two")
        with patch("experiments.deepgram_live._run_stream",
                   new_callable=AsyncMock, side_effect=[first, second]) as run:
            report = asyncio.run(run_trial(
                trial="C",
                key="local-test-key",
                source="internal-mic",
                duration_seconds=10,
                native_format="native",
                network_context="local",
            ))
        self.assertEqual(run.await_count, 2)
        self.assertTrue(run.await_args_list[0].kwargs["interrupt"])
        self.assertFalse(run.await_args_list[1].kwargs["interrupt"])
        self.assertEqual(run.await_args_list[0].kwargs["duration_seconds"], 5)
        self.assertTrue(report["behavior"]["reconnected"])

        with patch("experiments.deepgram_live._run_stream",
                   new_callable=AsyncMock, return_value=evidence("only")) as run:
            report = asyncio.run(run_trial(
                trial="A",
                key="local-test-key",
                source="internal-mic",
                duration_seconds=1,
                native_format="native",
                network_context="local",
            ))
        self.assertEqual(run.await_count, 1)
        self.assertFalse(run.await_args.kwargs["interrupt"])
        self.assertFalse(report["behavior"]["reconnected"])

        for trial, duration in (("D", 1), ("A", 0), ("A", 121)):
            with self.subTest(trial=trial, duration=duration), \
                    self.assertRaises(ValueError):
                asyncio.run(run_trial(
                    trial=trial,
                    key="local-test-key",
                    source="internal-mic",
                    duration_seconds=duration,
                    native_format="native",
                    network_context="local",
                ))

    def test_successful_cli_writes_private_aggregate_with_restrictive_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deepgram-output" / "success.json"
            report = {"aggregate": True, "recognized_text_persisted": False}
            with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "local-test-key"}), \
                    patch("experiments.deepgram_live.OUTPUT_ROOT", output.parent), \
                    patch("experiments.deepgram_live.run_trial",
                          new_callable=AsyncMock, return_value=report):
                self.assertEqual(main([
                    "--trial", "A",
                    "--duration", "1",
                    "--source", "internal-mic",
                    "--output", str(output),
                ]), 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with patch("experiments.deepgram_live.OUTPUT_ROOT", output.parent):
                self.assertEqual(_safe_output_path(output), output.resolve())
                with self.assertRaises(ValueError):
                    _safe_output_path(output.parent / "nested" / "result.json")

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

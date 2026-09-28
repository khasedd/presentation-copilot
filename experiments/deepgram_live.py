"""Bounded, non-production Deepgram Nova-3 microphone experiment.

Raw microphone bytes remain in process pipes and memory. The experiment writes
only aggregate measurements; transcript text and credentials are never logged or
persisted. Run only from an environment that can access the selected PipeWire
source and has the pinned WebSocket dependency installed.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Mapping, Sequence
from urllib.parse import urlencode

from transcription.adapters.deepgram import DeepgramAdapter, DeepgramAdapterError
from transcription.model import SegmentUpdated


LISTEN_URL = "wss://api.deepgram.com/v1/listen"
OUTPUT_ROOT = Path("deepgram-output")
PRICE_PER_MINUTE_USD = 0.0048
MAX_TRIAL_SECONDS = 240
TRIAL_COMPLETION_SILENCE_SECONDS = 8.0
TRIAL_MINIMUM_FINAL_TOKEN_RATIO = 0.80

PRESENTATION_SCRIPT = """Today I am demonstrating Presentation Copilot, a
privacy-conscious assistant for live technical talks. Audio enters through
PipeWire and WirePlumber, then a WebSocket sends sixteen kilohertz mono linear
sixteen samples to Deepgram Nova three. The adapter converts every provider
callback into TranscriptEvent version one point zero, preserving partial
revisions, final segments, timestamps, and explicit failure state. Our hackathon
stack also uses Nebius Token Factory and an NVIDIA Nemotron model for semantic
reasoning. Open Parakeet remains the documented challenger for a later
comparison. We send fifty millisecond chunks and wait five hundred milliseconds
for endpointing. The first test includes the numbers sixteen thousand, fifty,
five hundred, and ninety. After a normal pause, the transcript should settle
without inventing words. Um, the measurement uses provider timestamps—sorry,
the latency measurement uses a local sent-audio cursor, not provider timestamps
as a precision wall clock. If the network disconnects, the current stream fails
and a new stream begins with a fresh identifier. No missing cross-stream speech
is synthesized. Raw microphone audio stays in memory and is never saved by the
application. These safeguards keep the experiment bounded while we measure word
error rate, technical-term recall, interim churn, final availability, and safe
recovery."""

FAILURE_SCRIPT = """This failure trial checks conservative recovery during a
live presentation. The first WebSocket receives microphone audio until the
planned interruption. At that point the stream records an explicit failed
status and closes. A new connection then starts with a fresh stream identifier
and an empty transcript accumulator. Speech that occurs during the gap remains
missing; the program does not copy, guess, or reconcile words across the two
streams. After reconnecting, the presenter continues normally while the same
Nova three settings collect latency and endpoint measurements. This is a test
of visible degradation, not seamless recovery."""

TECHNICAL_TERMS = (
    "Presentation Copilot",
    "PipeWire",
    "WirePlumber",
    "WebSocket",
    "linear sixteen",
    "Deepgram",
    "Nova three",
    "TranscriptEvent",
    "Nebius Token Factory",
    "NVIDIA Nemotron",
    "Open Parakeet",
)


class LiveExperimentError(RuntimeError):
    """Content-free experiment failure safe to display."""


@dataclass(frozen=True)
class ListenConfig:
    sample_rate: int = 16_000
    channels: int = 1
    sample_width_bytes: int = 2
    chunk_ms: int = 50
    endpointing_ms: int = 500

    @property
    def chunk_bytes(self) -> int:
        return (self.sample_rate * self.channels * self.sample_width_bytes
                * self.chunk_ms // 1000)


@dataclass
class _SentAudioClock:
    config: ListenConfig
    byte_count: int = 0
    cursors: deque[tuple[float, float]] = field(default_factory=deque)

    def sent(self, byte_count: int, sent_at: float) -> None:
        self.byte_count += byte_count
        self.cursors.append((audio_cursor_ms(self.byte_count, self.config), sent_at))

    def lag_ms(self, provider_end_ms: float, observed_at: float) -> float | None:
        for cursor_ms, sent_at in self.cursors:
            if cursor_ms >= provider_end_ms:
                return max(0.0, (observed_at - sent_at) * 1000)
        return None


@dataclass
class _StreamEvidence:
    stream_id: str
    adapter: DeepgramAdapter
    sent_bytes: int = 0
    provider_duration_seconds: float | None = None
    interim_lags_ms: list[float] = field(default_factory=list)
    final_lags_ms: list[float] = field(default_factory=list)
    partial_events: int = 0
    partial_revisions: int = 0
    final_events: int = 0
    shorter_finals: int = 0
    endpoint_events: int = 0
    timestamps_monotonic: bool = True
    last_final_end_ms: int = 0
    disconnect_detected: bool = False
    completion_reason: str | None = None

    @property
    def final_text(self) -> str:
        state = self.adapter.accumulator.state
        if state is None:
            return ""
        return " ".join(segment.text for segment in state.segments
                        if segment.status == "final")


@dataclass
class _SpeechCompletion:
    """Recognize a completed scripted read without retaining microphone audio."""

    minimum_final_tokens: int
    silence_seconds: float
    endpoint_observed_at: float | None = None

    def observe(self, message: Mapping[str, object], *, observed_at: float) -> None:
        message_type = message.get("type")
        if message_type == "SpeechStarted":
            self.endpoint_observed_at = None
            return
        if message_type == "UtteranceEnd":
            self.endpoint_observed_at = observed_at
            return
        if message_type != "Results":
            return

        channel = message.get("channel")
        alternatives = channel.get("alternatives") if isinstance(channel, dict) else None
        first = alternatives[0] if isinstance(alternatives, list) and alternatives else None
        transcript = first.get("transcript") if isinstance(first, dict) else None
        if isinstance(transcript, str) and transcript.strip():
            self.endpoint_observed_at = None
        if message.get("speech_final") is True:
            self.endpoint_observed_at = observed_at

    def ready(self, *, observed_at: float, final_text: str) -> bool:
        return (
            self.endpoint_observed_at is not None
            and observed_at - self.endpoint_observed_at >= self.silence_seconds
            and len(_tokens(final_text)) >= self.minimum_final_tokens
        )


def load_deepgram_key(
    environment: Mapping[str, str], env_path: Path = Path(".env")
) -> str | None:
    """Read a key as data; never source or execute a local environment file."""
    if value := environment.get("DEEPGRAM_API_KEY"):
        return value
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "DEEPGRAM_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value or None
    return None


def build_listen_url(config: ListenConfig = ListenConfig()) -> str:
    query = {
        "model": "nova-3",
        "language": "en-US",
        "encoding": "linear16",
        "sample_rate": str(config.sample_rate),
        "channels": str(config.channels),
        "interim_results": "true",
        "mip_opt_out": "true",
        "endpointing": str(config.endpointing_ms),
        "vad_events": "true",
        "punctuate": "true",
        "smart_format": "true",
    }
    return LISTEN_URL + "?" + urlencode(query)


def capture_command(source: str, config: ListenConfig = ListenConfig()) -> list[str]:
    if not source or source.startswith("-") or any(char.isspace() for char in source):
        raise ValueError("A single explicit PipeWire-Pulse source name is required")
    return [
        "parec",
        f"--device={source}",
        "--raw",
        "--format=s16le",
        f"--rate={config.sample_rate}",
        f"--channels={config.channels}",
        f"--latency-msec={config.chunk_ms}",
        "--client-name=Presentation Copilot Deepgram POC",
        "--stream-name=bounded in-memory capture",
    ]


def audio_cursor_ms(byte_count: int, config: ListenConfig = ListenConfig()) -> float:
    if type(byte_count) is not int or byte_count < 0:
        raise ValueError("Audio byte count must be a nonnegative integer")
    bytes_per_second = config.sample_rate * config.channels * config.sample_width_bytes
    return byte_count * 1000 / bytes_per_second


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected = _tokens(reference)
    actual = _tokens(hypothesis)
    if not expected:
        raise ValueError("Reference text must contain at least one word")
    previous = list(range(len(actual) + 1))
    for row, expected_word in enumerate(expected, start=1):
        current = [row]
        for column, actual_word in enumerate(actual, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (expected_word != actual_word),
            ))
        previous = current
    return previous[-1] / len(expected)


def technical_term_recall(hypothesis: str, terms: Sequence[str]) -> tuple[float, int]:
    if not terms:
        raise ValueError("At least one technical term is required")
    normalized = " ".join(_tokens(hypothesis))
    matched = sum(" ".join(_tokens(term)) in normalized for term in terms)
    return matched / len(terms), matched


def _percentile(samples: Sequence[float], percentage: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(float(sample) for sample in samples)
    rank = max(1, math.ceil(percentage * len(ordered)))
    return round(ordered[rank - 1], 3)


def _latency_summary(samples: Sequence[float]) -> dict[str, float | int | None]:
    return {
        "sample_count": len(samples),
        "p50": _percentile(samples, 0.50),
        "p95": _percentile(samples, 0.95),
    }


def safe_trial_report(
    *,
    trial: str,
    duration_seconds: float,
    billable_seconds: float,
    wer: float | None,
    term_recall: float | None,
    matched_terms: int,
    total_terms: int,
    interim_lags_ms: Sequence[float],
    final_lags_ms: Sequence[float],
    partial_events: int,
    partial_revisions: int,
    final_events: int,
    shorter_finals: int,
    endpoint_events: int,
    timestamps_monotonic: bool,
    disconnect_detected: bool,
    reconnected: bool,
    stream_ids: Sequence[str],
    selected_source: str,
    native_format: str,
    network_context: str,
) -> dict[str, object]:
    """Return aggregate-only evidence with no transcript or account content."""
    return {
        "trial": trial,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "requested_duration_seconds": round(duration_seconds, 3),
        "billable_duration_seconds": round(billable_seconds, 3),
        "estimated_cost_usd": round(
            billable_seconds / 60 * PRICE_PER_MINUTE_USD, 6),
        "accuracy": {
            "wer": None if wer is None else round(wer, 6),
            "technical_term_recall": (
                None if term_recall is None else round(term_recall, 6)),
            "matched_terms": matched_terms,
            "total_terms": total_terms,
        },
        "latency_ms": {
            "interim": _latency_summary(interim_lags_ms),
            "final": _latency_summary(final_lags_ms),
            "measurement_source": "local sent-audio cursor and monotonic clock",
        },
        "behavior": {
            "partial_events": partial_events,
            "partial_revisions": partial_revisions,
            "final_events": final_events,
            "shorter_finals": shorter_finals,
            "endpoint_events": endpoint_events,
            "timestamps_monotonic": timestamps_monotonic,
            "disconnect_detected": disconnect_detected,
            "reconnected": reconnected,
            "stream_ids": list(stream_ids),
        },
        "configuration": {
            "model": "nova-3",
            "language": "en-US",
            "selected_source": selected_source,
            "native_format": native_format,
            "transmitted_format": "16000 Hz, mono, linear16",
            "chunk_ms": 50,
            "endpointing_ms": 500,
            "diarization": False,
            "network_context": network_context,
        },
        "privacy": {
            "mip_opt_out_requested": True,
            "raw_audio_persisted": False,
            "recognized_text_persisted": False,
            "credential_persisted": False,
        },
    }


def _provider_end_ms(message: dict[str, object]) -> float:
    start = message.get("start")
    duration = message.get("duration")
    if (not isinstance(start, (int, float)) or isinstance(start, bool)
            or not isinstance(duration, (int, float)) or isinstance(duration, bool)):
        raise LiveExperimentError("Provider result omitted valid timing")
    return (float(start) + float(duration)) * 1000


def _update_evidence(
    evidence: _StreamEvidence,
    message: dict[str, object],
    events,
    lag_ms: float | None,
) -> None:
    updates = [event.payload for event in events
               if isinstance(event.payload, SegmentUpdated)]
    if not updates:
        return
    is_final = message.get("is_final") is True
    if message.get("speech_final") is True:
        evidence.endpoint_events += 1
    if len(events) == 2:
        evidence.shorter_finals += 1
    for payload in updates:
        if payload.status == "partial":
            evidence.partial_events += 1
            if payload.revision > 1:
                evidence.partial_revisions += 1
        else:
            evidence.final_events += 1
            if payload.end_ms is not None:
                if payload.end_ms < evidence.last_final_end_ms:
                    evidence.timestamps_monotonic = False
                evidence.last_final_end_ms = max(
                    evidence.last_final_end_ms, payload.end_ms)
    if lag_ms is not None:
        (evidence.final_lags_ms if is_final else evidence.interim_lags_ms).append(lag_ms)


async def _run_stream(
    *,
    key: str,
    source: str,
    session_id: str,
    duration_seconds: float,
    config: ListenConfig,
    started_at: datetime,
    interrupt: bool,
    completion: _SpeechCompletion | None = None,
) -> _StreamEvidence:
    try:
        import websockets
        from websockets.exceptions import ConnectionClosed
    except ImportError as error:
        raise LiveExperimentError(
            "Install requirements-deepgram-poc.txt before live use") from error

    adapter = DeepgramAdapter(
        session_id=session_id,
        source_id=source,
        started_at=started_at,
    )
    evidence = _StreamEvidence(stream_id=adapter.stream_id, adapter=adapter)
    clock = _SentAudioClock(config)
    stream_started = time.monotonic()
    capture = None
    websocket = None
    intentional_disconnect = False

    def current_observed_ms() -> int:
        elapsed_ms = max(0, round((time.monotonic() - stream_started) * 1000))
        state = adapter.accumulator.state
        return max(elapsed_ms, state.observed_at_ms if state else 0)

    try:
        websocket = await websockets.connect(
            build_listen_url(config),
            additional_headers={"Authorization": f"Token {key}"},
            open_timeout=15,
            close_timeout=5,
            ping_interval=20,
            max_size=1_048_576,
        )
        capture = await asyncio.create_subprocess_exec(
            *capture_command(source, config),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if capture.stdout is None:
            raise LiveExperimentError("Microphone capture pipe is unavailable")

        async def sender() -> None:
            nonlocal intentional_disconnect
            deadline = stream_started + duration_seconds
            while True:
                now = time.monotonic()
                if completion is not None and completion.ready(
                        observed_at=now, final_text=evidence.final_text):
                    evidence.completion_reason = "speech_complete"
                    break
                if now >= deadline:
                    evidence.completion_reason = "max_duration"
                    break
                chunk = await capture.stdout.readexactly(config.chunk_bytes)
                await websocket.send(chunk)
                sent_at = time.monotonic()
                clock.sent(len(chunk), sent_at)
                evidence.sent_bytes += len(chunk)
            if interrupt:
                intentional_disconnect = True
                await websocket.close(code=1011, reason="intentional POC interruption")
                return
            await websocket.send(json.dumps({"type": "Finalize"}))
            await asyncio.sleep(1.0)
            await websocket.send(json.dumps({"type": "CloseStream"}))

        send_task = asyncio.create_task(sender())
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=5)
                except asyncio.TimeoutError:
                    if send_task.done():
                        break
                    continue
                except ConnectionClosed:
                    break
                if not isinstance(raw, str) or len(raw.encode("utf-8")) > 1_048_576:
                    raise LiveExperimentError("Provider returned an invalid message envelope")
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError as error:
                    raise LiveExperimentError("Provider returned invalid JSON") from error
                if not isinstance(message, dict):
                    raise LiveExperimentError("Provider returned an invalid message envelope")
                if message.get("type") == "Metadata":
                    duration = message.get("duration")
                    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                        evidence.provider_duration_seconds = float(duration)
                    adapter.accept(message, observed_at_ms=max(
                        0, round((time.monotonic() - stream_started) * 1000)))
                    continue
                if message.get("type") in {"SpeechStarted", "UtteranceEnd"}:
                    if completion is not None:
                        completion.observe(message, observed_at=time.monotonic())
                    adapter.accept(message, observed_at_ms=max(
                        0, round((time.monotonic() - stream_started) * 1000)))
                    continue
                if message.get("type") != "Results":
                    raise LiveExperimentError("Provider returned an unexpected message type")
                observed_at = time.monotonic()
                provider_end_ms = _provider_end_ms(message)
                observed_ms = max(
                    round((observed_at - stream_started) * 1000),
                    math.ceil(provider_end_ms),
                )
                events = adapter.accept(message, observed_at_ms=observed_ms)
                if completion is not None:
                    completion.observe(message, observed_at=observed_at)
                lag = clock.lag_ms(provider_end_ms, observed_at)
                _update_evidence(evidence, message, events, lag)
            await send_task
        finally:
            if not send_task.done():
                send_task.cancel()
                await asyncio.gather(send_task, return_exceptions=True)

        observed_ms = current_observed_ms()
        if intentional_disconnect:
            adapter.fail(observed_at_ms=observed_ms, code="intentional_disconnect")
            evidence.disconnect_detected = True
        elif adapter.accumulator.state and adapter.accumulator.state.end_reason is None:
            adapter.close(observed_at_ms=observed_ms)
        return evidence
    except DeepgramAdapterError as error:
        raise LiveExperimentError(f"Adapter rejected provider behavior: {error.code}") from error
    except Exception as error:
        if websocket is not None and adapter.accumulator.state \
                and adapter.accumulator.state.end_reason is None:
            observed_ms = current_observed_ms()
            adapter.fail(observed_at_ms=observed_ms, code="transport_failure")
        if isinstance(error, LiveExperimentError):
            raise
        raise LiveExperimentError("Live Deepgram stream failed") from error
    finally:
        if capture is not None and capture.returncode is None:
            capture.terminate()
            try:
                await asyncio.wait_for(capture.wait(), timeout=3)
            except asyncio.TimeoutError:
                capture.kill()
                await capture.wait()


def _combine_report(
    *,
    trial: str,
    requested_duration: float,
    streams: Sequence[_StreamEvidence],
    source: str,
    native_format: str,
    network_context: str,
    reference: str,
) -> dict[str, object]:
    billable_seconds = sum(
        item.provider_duration_seconds
        if item.provider_duration_seconds is not None
        else audio_cursor_ms(item.sent_bytes) / 1000
        for item in streams
    )
    # Accuracy is reported for uninterrupted A/B only. Concatenating Trial C's
    # streams would conceal missing cross-stream speech, so it remains unknown.
    hypothesis = streams[0].final_text if len(streams) == 1 else ""
    wer = word_error_rate(reference, hypothesis) if len(streams) == 1 else None
    recall, matched = (technical_term_recall(hypothesis, TECHNICAL_TERMS)
                       if len(streams) == 1 else (None, 0))
    report = safe_trial_report(
        trial=trial,
        duration_seconds=requested_duration,
        billable_seconds=billable_seconds,
        wer=wer,
        term_recall=recall,
        matched_terms=matched,
        total_terms=len(TECHNICAL_TERMS) if len(streams) == 1 else 0,
        interim_lags_ms=tuple(value for item in streams for value in item.interim_lags_ms),
        final_lags_ms=tuple(value for item in streams for value in item.final_lags_ms),
        partial_events=sum(item.partial_events for item in streams),
        partial_revisions=sum(item.partial_revisions for item in streams),
        final_events=sum(item.final_events for item in streams),
        shorter_finals=sum(item.shorter_finals for item in streams),
        endpoint_events=sum(item.endpoint_events for item in streams),
        timestamps_monotonic=all(item.timestamps_monotonic for item in streams),
        disconnect_detected=any(item.disconnect_detected for item in streams),
        reconnected=len(streams) > 1,
        stream_ids=tuple(item.stream_id for item in streams),
        selected_source=source,
        native_format=native_format,
        network_context=network_context,
    )
    report["privacy"]["live_handshake_accepted_mip_parameter"] = True  # type: ignore[index]
    return report


async def run_trial(
    *,
    trial: str,
    key: str,
    source: str,
    duration_seconds: float,
    native_format: str,
    network_context: str,
) -> dict[str, object]:
    if trial not in {"A", "B", "C"}:
        raise ValueError("Trial must be A, B, or C")
    if not 1 <= duration_seconds <= MAX_TRIAL_SECONDS:
        raise ValueError("Trial duration must be between 1 and 240 seconds")
    config = ListenConfig()
    session_id = f"deepgram-poc-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    reference = PRESENTATION_SCRIPT if trial in {"A", "B"} else FAILURE_SCRIPT
    streams: list[_StreamEvidence] = []
    if trial == "C":
        first_duration = duration_seconds / 2
        first = await _run_stream(
            key=key, source=source, session_id=session_id,
            duration_seconds=first_duration, config=config,
            started_at=datetime.now(timezone.utc), interrupt=True,
        )
        streams.append(first)
        second = await _run_stream(
            key=key, source=source, session_id=session_id,
            duration_seconds=duration_seconds - first_duration, config=config,
            started_at=datetime.now(timezone.utc), interrupt=False,
        )
        streams.append(second)
    else:
        completion = _SpeechCompletion(
            minimum_final_tokens=math.ceil(
                len(_tokens(reference)) * TRIAL_MINIMUM_FINAL_TOKEN_RATIO),
            silence_seconds=TRIAL_COMPLETION_SILENCE_SECONDS,
        )
        stream = await _run_stream(
            key=key, source=source, session_id=session_id,
            duration_seconds=duration_seconds, config=config,
            started_at=datetime.now(timezone.utc), interrupt=False,
            completion=completion,
        )
        if stream.completion_reason == "max_duration":
            raise LiveExperimentError(
                "Trial reached its safety limit before the presenter finished")
        if stream.completion_reason != "speech_complete":
            raise LiveExperimentError(
                "Trial ended before presenter completion was confirmed")
        streams.append(stream)
    return _combine_report(
        trial=trial,
        requested_duration=duration_seconds,
        streams=streams,
        source=source,
        native_format=native_format,
        network_context=network_context,
        reference=reference,
    )


def _safe_output_path(path: Path) -> Path:
    root = OUTPUT_ROOT.resolve()
    resolved = path.resolve()
    if resolved.parent != root or resolved.suffix != ".json":
        raise ValueError("Output must be a direct JSON child of deepgram-output")
    return resolved


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", choices=("A", "B", "C"), required=True)
    parser.add_argument(
        "--duration", type=float, required=True,
        help="hard safety limit in seconds; A/B stop after confirmed end silence",
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--native-format", default="48000 Hz, 2 channels, s16")
    parser.add_argument("--network-context", default="local network")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    key = load_deepgram_key(os.environ)
    if not key:
        parser.error("DEEPGRAM_API_KEY is required locally")
    try:
        output = _safe_output_path(args.output)
        output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor: int | None = os.open(
            output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            report = asyncio.run(run_trial(
                trial=args.trial,
                key=key,
                source=args.source,
                duration_seconds=args.duration,
                native_format=args.native_format,
                network_context=args.network_context,
            ))
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = None
                json.dump(report, handle, indent=2, sort_keys=True)
                handle.write("\n")
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            output.unlink(missing_ok=True)
            raise
        print(f"Trial {args.trial} complete; aggregate evidence written to {output}")
        return 0
    except FileExistsError:
        parser.error("Output already exists; refusing to overwrite evidence")
    except (LiveExperimentError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

# Phase 3 — Transcript contract and deterministic replay

Implemented and verified September 26, 2026, on `codex/phase-3-transcript-contract`. This is the first Phase 3 slice: a provider-independent internal event model, a transcript-only accumulator, and deterministic mock/replay input. The Phase 3 exit gate remains incomplete. No microphone, transcription provider, semantic coverage integration, presentation control, or application session orchestration is implemented.

## Architecture and scope

`transcription/` follows Phase 2's standard-library Python, frozen dataclasses, explicit validation, and provider boundary conventions. It does not import `presentation/` or the semantic-coverage experiments. Deck schema 1.0, `SourceRevision`, ingestion and snapshot-comparison behavior remain unchanged. Transcript schema 1.0 is independently versioned.

- `model.py` owns events, per-event validation and exact-schema JSON serialization/decoding.
- `stream.py` owns one ordered transcript stream and validates cross-event transitions.
- `replay.py` reads small UTF-8 JSON event arrays and feeds those events through the same accumulator future adapters will use.

No dependencies or services were added. The existing substantive Nebius/NVIDIA path is untouched. Live transcription selection still requires the roadmap's technical, privacy, licensing and current hackathon-rules investigation; this slice makes no new provider/compliance claim.

## Event schema 1.0

`TranscriptEvent` is frozen and validates its payload and provenance at construction. Standalone payload/provenance objects are data holders until wrapped in an event, except that `StreamStarted` immediately validates/canonicalizes its optional datetime. Serialization and accumulator entry also validate events.

| Envelope field | Meaning |
| --- | --- |
| `schema_version` | Exactly `"1.0"` |
| `session_id`, `stream_id` | Nonempty opaque strings; the pair identifies a continuous stream within a session |
| `sequence` | Nonnegative normalized internal event counter |
| `observed_at_ms` | Nonnegative integer offset from stream start when the normalized event was observed |
| `provenance` | Frozen `Provenance` described below |
| `payload` | Exactly one of the four typed variants below |

`Provenance` has `origin: "synthetic" | "transcriber"`, `delivery: "replay" | "live"`, `source_id: str`, and `provider: str | None`. The source ID identifies a fixture or input source; provider is an optional descriptive label, not an integration. Origin and delivery are independent: replaying a future recorded transcriber stream retains `origin="transcriber"` and its provider/source labels while setting `delivery="replay"`. Identifiers are not credentials or persistent user identities.

| Payload | Fields beyond its fixed `kind` discriminator |
| --- | --- |
| `StreamStarted`, `kind="stream_started"` | `started_at: datetime \| None` |
| `SegmentUpdated`, `kind="segment_updated"` | `segment_id: str`, `segment_index: int`, `revision: int`, `status: "partial" \| "final"`, `text: str`, `start_ms: int \| None`, `end_ms: int \| None`, `speaker_id: str \| None` |
| `StreamStatusChanged`, `kind="stream_status_changed"` | `status: "ready" \| "delayed" \| "missing" \| "failed"` |
| `StreamEnded`, `kind="stream_ended"` | `reason: "completed" \| "cancelled" \| "failed"` |

### Counters and ordering

`sequence` and `revision` are **internal counters owned by our adapter/model boundary**, not requirements on provider output. A future adapter must normalize its provider's callbacks, IDs, duplicates, and revisions before downstream consumption. This slice validates normalized counters; it does not implement a provider normalizer or silently repair input.

A start event has sequence `0` and observation offset `0`. Every subsequent event must have the next consecutive sequence. All event kinds consume a sequence. Observation offsets must not decrease, but equal offsets are valid; sequence breaks ties. Audio timing does not determine delivery order.

A new segment must have revision `1` and the next consecutive, zero-based `segment_index`. Indices describe first-observed order, not guaranteed acoustic chronology. Revisions preserve both segment ID and index and increase by exactly one. Full identity is `(session_id, stream_id, segment_id)`; a segment ID alone is insufficient. Provider ID mapping and first-observed ordering are future adapter responsibilities.

### Time and serialization

`started_at` is optional metadata for an absolute start instant. It is never generated from a wall clock here. When supplied, it must be timezone-aware and convertible to UTC; naive datetimes are rejected. The model normalizes it to UTC. `event_to_json` writes exactly `YYYY-MM-DDTHH:MM:SS.ffffffZ`, including six fractional digits even when zero. Equivalent instants with different supplied offsets produce identical JSON.

The JSON decoder accepts uppercase `T`/`Z`, valid explicit offsets, and zero to six fractional-second digits. It rejects naive timestamps, unknown `-00:00` offsets, invalid offset minutes/hours, invalid calendar dates, leap seconds, and precision beyond microseconds. This is a documented timestamp subset, not a general-purpose RFC parser.

Segment offsets are integer audio positions relative to the same stream origin: both unknown (`None`/JSON `null`), or `0 <= start_ms <= end_ms <= observed_at_ms`. Overlap and equal audio positions are allowed. A revision may correct offsets, including changing known timing to unknown. Speaker labels are optional, nonempty when present, and stream-local; no diarization or speaker identity inference runs. Booleans are rejected as counters/offsets.

JSON preserves exact text, including whitespace, Unicode, and empty strings. Serialization sorts keys, uses two-space indentation and a trailing newline. Decoding requires the exact envelope/provenance/payload fields, with explicit nulls for optional values. Unknown/missing fields, duplicate keys, nonfinite numbers and unknown schema/payload kinds fail instead of being ignored. `event_from_dict` accepts an already-decoded object; callers needing duplicate-key checks must use `event_from_json` or `load_replay`.

## Accumulator behavior

`TranscriptAccumulator.apply(event)` returns a frozen `TranscriptState`. Before a start event, `state` is `None`. Afterward, state contains session/stream identity, provenance, optional start instant, last accepted sequence/observation offset, ordered latest segments, current availability status, status-event history, and optional end reason.

Each accepted update replaces the entire prior version of its segment. For example, `Our late city` (partial revision 1) becomes `Our latency` (partial revision 2), then a final sentence (revision 3). Text is not concatenated. A later final revision may correct that sentence; final cannot revert to partial. A segment may also arrive already final at revision 1. An empty replacement stays explicit; it does not delete or renumber the segment.

Session, stream, and provenance remain constant throughout an accumulator's lifetime. Repeated starts, wrong identities, stale/duplicate/skipped counters, decreasing observation offsets, index changes and final-to-partial updates raise `TranscriptValidationError` without changing accepted state. Earlier returned states remain immutable snapshots.

| Availability or boundary | Behavior |
| --- | --- |
| Start | Current status becomes `ready`; this indicates stream availability, not transcript completeness |
| `delayed` / `missing` | Preserve existing segments and append the explicit status event to history; invent no text or finality |
| `ready` after degradation | Restore current availability; preserve historical missing/delayed events |
| New segment while degraded | Accept if valid, but do not implicitly restore readiness |
| `failed` | Preserve state/evidence; only a subsequent `StreamEnded(reason="failed")` is allowed |
| End | Record the reason; retain unfinished partials and availability history; reject all subsequent events |
| Direct failed end | Allowed without a preceding failed status event; sets status and end reason to `failed` |
| Reconnection/new session | Use a fresh accumulator and new stream ID; counters reset, and old-stream events are rejected |

`completed` means the producer explicitly closed the stream, not that every segment is final or missing audio was recovered. End events do not clear degraded status. Status history identifies when degradation was reported; it does not establish exact lost-audio intervals or prove that lost speech has been recovered. The producer must emit explicit status changes; no timeout detector runs here.

The accumulator is single-writer, in-memory, and scoped to one stream. It retains the latest version of each segment and all status events, not a persistent revision log. Replay callers can retain returned snapshots when needed. It does not enforce global ID uniqueness across separately created accumulators; the future session owner must allocate distinct stream IDs and manage overall session boundaries. Split/merge corrections and cross-stream transcript reconciliation are deferred.

## Deterministic replay

`load_replay(path)` yields typed events from an ordered JSON array. `replay(events)` creates a fresh accumulator and yields a state after each accepted event. Both mark delivery as replay and preserve origin, source/provider labels, session/stream IDs, counters, and timestamps. They never sort, sleep, call a clock, access a network, or capture audio. The only replay I/O is reading the supplied fixture file.

Consume the iterator to exhaustion to validate closure. An empty or truncated replay raises `TranscriptValidationError(code="incomplete_stream")`; malformed events and transitions use `invalid_event` and `invalid_transition`. Earlier yielded states may be valid observations even if a later event fails. There is no synthesized end event or success claim on early iterator abandonment. A failed stream that closes explicitly is a valid replay of failure, not an operationally successful transcription.

The committed synthetic fixture has ten events: partial correction, finalization, delayed/missing/recovered availability, a second unfinished segment, a correction to the first final, and closure. Its timing is authored test data, not latency measurement. A library-level check from the repository root:

```bash
python3 - <<'PY'
from transcription.replay import load_replay, replay

states = tuple(replay(load_replay("tests/fixtures/transcript_evolution.json")))
assert len(states) == 10
assert states[-1].segments[0].revision == 4
assert states[-1].segments[1].status == "partial"
assert states[-1].end_reason == "completed"
print(f"Replayed {len(states)} events; {len(states[-1].segments)} segments")
PY
python3 -m unittest discover -s tests -v
```

The fixture reader loads a whole small file; it is not a bounded production upload API or long-session storage system. Missing/unreadable file errors propagate to the caller; malformed JSON/UTF-8 errors are sanitized. No transcript is printed by the library. Objects/serialized JSON contain potentially sensitive text, so callers must avoid logging them; only synthetic content belongs in committed fixtures. This slice introduces no live recording or retention policy.

## Verification and remaining Phase 3 work

All **74 repository tests passed**: 41 existing tests and 33 transcript tests. Tests verify canonical UTC serialization, strict schema checks, corrected/final evolution, first-observed order, atomic rejection, stream/session isolation, degraded/failure behavior, truncated input, replay provenance, UTF-8 handling and deterministic fixture-to-state replay. Standard-library `trace` line coverage reports model 100.0%, replay 100.0%, and stream 98.6%; this is line coverage, not branch coverage. See [test evidence](testing/transcript-replay.tdd.md) for commands, checkpoint history, and limitations.

Remaining work retains the roadmap's intended scope:

1. Investigate audio-capture permissions, device selection, consent/privacy expectations, and permitted transcription components.
2. Investigate/select a technically and legally suitable live transcription path, including current hackathon compatibility. No provider is selected here.
3. Implement capture/streaming and an adapter that normalizes provider callbacks, timing, internal counters, identities, partial/final corrections and failure/recovery into this contract. Determine transport, backpressure, loss detection, cancellation and clock-alignment policies from actual provider behavior.
4. Run realistic presentation trials and record delay, accuracy, partial-result stability and failure behavior, with limitations. Replay is not a substitute for this live gate evidence.

The approved model and file plan were retained. Decoder strictness for invalid/unknown timestamp offsets is a narrowly scoped implementation clarification supporting the approved known, timezone-aware start instant. No Phase 4 integration or Phase 5 application state was introduced. The Phase 3 exit gate remains incomplete.

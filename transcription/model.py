"""Immutable internal events. Provider counters must be normalized by adapters.

Sequence orders observations; segment timestamps describe audio, not delivery.
This schema is independent of presentation snapshots and coverage decisions.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Literal

SCHEMA_VERSION = "1.0"
StreamStatus = Literal["ready", "delayed", "missing", "failed"]
EndReason = Literal["completed", "cancelled", "failed"]


class TranscriptValidationError(ValueError):
    """Content-free diagnostics safe to report without printing a transcript."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TranscriptValidationError("invalid_event", message)


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _counter(value: object, minimum: int = 0) -> bool:
    # bool subclasses int, but true/false are not normalized counters or offsets.
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _utc(value: datetime) -> datetime:
    _require(isinstance(value, datetime), "started_at must be a datetime")
    _require(value.tzinfo is not None and value.utcoffset() is not None,
             "started_at must be timezone-aware")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise TranscriptValidationError("invalid_event", "started_at is outside UTC range") from None


@dataclass(frozen=True)
class Provenance:
    origin: Literal["synthetic", "transcriber"]
    delivery: Literal["replay", "live"]
    source_id: str
    provider: str | None


@dataclass(frozen=True)
class StreamStarted:
    started_at: datetime | None = None
    kind: Literal["stream_started"] = field(default="stream_started", init=False)

    def __post_init__(self) -> None:
        if self.started_at is not None:
            object.__setattr__(self, "started_at", _utc(self.started_at))


@dataclass(frozen=True)
class SegmentUpdated:
    segment_id: str
    segment_index: int
    revision: int
    status: Literal["partial", "final"]
    text: str
    start_ms: int | None
    end_ms: int | None
    speaker_id: str | None
    kind: Literal["segment_updated"] = field(default="segment_updated", init=False)


@dataclass(frozen=True)
class StreamStatusChanged:
    status: StreamStatus
    kind: Literal["stream_status_changed"] = field(default="stream_status_changed", init=False)


@dataclass(frozen=True)
class StreamEnded:
    reason: EndReason
    kind: Literal["stream_ended"] = field(default="stream_ended", init=False)


TranscriptPayload = StreamStarted | SegmentUpdated | StreamStatusChanged | StreamEnded


@dataclass(frozen=True)
class TranscriptEvent:
    schema_version: str
    session_id: str
    stream_id: str
    sequence: int
    observed_at_ms: int
    provenance: Provenance
    payload: TranscriptPayload

    def __post_init__(self) -> None:
        validate_event(self)


def validate_event(event: TranscriptEvent) -> None:
    """Validate one event; cross-event invariants belong to the accumulator."""
    _require(isinstance(event, TranscriptEvent), "Expected a transcript event")
    _require(event.schema_version == SCHEMA_VERSION, "Unsupported transcript schema")
    _require(_identifier(event.session_id) and _identifier(event.stream_id),
             "Session and stream identifiers are required")
    _require(_counter(event.sequence), "sequence must be a nonnegative integer")
    _require(_counter(event.observed_at_ms), "observed_at_ms must be a nonnegative integer")
    provenance = event.provenance
    _require(isinstance(provenance, Provenance), "Expected transcript provenance")
    _require(provenance.origin in ("synthetic", "transcriber"), "Invalid transcript origin")
    _require(provenance.delivery in ("replay", "live"), "Invalid transcript delivery")
    _require(_identifier(provenance.source_id), "A source identifier is required")
    _require(provenance.provider is None or _identifier(provenance.provider),
             "Provider must be absent or a nonempty label")

    payload = event.payload
    if isinstance(payload, StreamStarted):
        if payload.started_at is not None:
            _utc(payload.started_at)
    elif isinstance(payload, SegmentUpdated):
        _require(_identifier(payload.segment_id), "A segment identifier is required")
        _require(_counter(payload.segment_index), "segment_index must be a nonnegative integer")
        _require(_counter(payload.revision, 1), "revision must be a positive integer")
        _require(payload.status in ("partial", "final"), "Invalid segment status")
        _require(isinstance(payload.text, str), "Segment text must be a string")
        _require(payload.speaker_id is None or _identifier(payload.speaker_id),
                 "Speaker must be absent or a nonempty label")
        if payload.start_ms is not None or payload.end_ms is not None:
            _require(_counter(payload.start_ms) and _counter(payload.end_ms),
                     "Audio offsets must both be unknown or nonnegative integers")
            _require(payload.start_ms <= payload.end_ms <= event.observed_at_ms,
                     "Audio offsets must be ordered and no later than observation")
    elif isinstance(payload, StreamStatusChanged):
        _require(payload.status in ("ready", "delayed", "missing", "failed"),
                 "Invalid stream status")
    elif isinstance(payload, StreamEnded):
        _require(payload.reason in ("completed", "cancelled", "failed"), "Invalid end reason")
    else:
        raise TranscriptValidationError("invalid_event", "Unknown transcript payload")


def event_to_json(event: TranscriptEvent) -> str:
    """Serialize using sorted keys and UTC RFC 3339 with six fractional digits."""
    validate_event(event)
    data = asdict(event)
    if isinstance(event.payload, StreamStarted) and event.payload.started_at is not None:
        data["payload"]["started_at"] = _utc(event.payload.started_at).isoformat(
            timespec="microseconds").replace("+00:00", "Z")
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise TranscriptValidationError("invalid_event", "Nonfinite JSON number")


def _decode_json(raw: str) -> object:
    """Shared strict decoder for single events and replay arrays."""
    try:
        return json.loads(raw, object_pairs_hook=_json_object, parse_constant=_invalid_constant)
    except (ValueError, TypeError, RecursionError):
        raise TranscriptValidationError("invalid_event", "Invalid transcript JSON") from None


def _fields(data: object, model: type) -> dict:
    _require(isinstance(data, dict), "Expected a JSON object")
    _require(set(data) == {item.name for item in fields(model)}, "Unexpected or missing JSON fields")
    return dict(data)


def event_from_dict(data: object) -> TranscriptEvent:
    """Decode an exact schema 1.0 object; unknown fields require schema evolution."""
    values = _fields(data, TranscriptEvent)
    values["provenance"] = Provenance(**_fields(values["provenance"], Provenance))
    payload = values["payload"]
    _require(isinstance(payload, dict), "Expected a payload object")
    models = {"stream_started": StreamStarted, "segment_updated": SegmentUpdated,
              "stream_status_changed": StreamStatusChanged, "stream_ended": StreamEnded}
    kind = payload.get("kind")
    _require(isinstance(kind, str) and kind in models, "Unknown transcript payload")
    model = models[kind]
    args = _fields(payload, model)
    args.pop("kind")
    if model is StreamStarted and args["started_at"] is not None:
        timestamp = args["started_at"]
        _require(isinstance(timestamp, str) and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
            timestamp) is not None, "started_at must be an aware RFC 3339 timestamp")
        try:
            args["started_at"] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise TranscriptValidationError("invalid_event", "Invalid started_at timestamp") from None
    values["payload"] = model(**args)
    return TranscriptEvent(**values)


def event_from_json(raw: str) -> TranscriptEvent:
    return event_from_dict(_decode_json(raw))

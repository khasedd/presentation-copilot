"""Single-stream transcript accumulation; no presentation or coverage state."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from transcription.model import (
    EndReason, Provenance, SegmentUpdated, StreamEnded, StreamStarted, StreamStatus,
    StreamStatusChanged, TranscriptEvent, TranscriptValidationError, validate_event,
)


@dataclass(frozen=True)
class TranscriptState:
    session_id: str
    stream_id: str
    provenance: Provenance
    started_at: datetime | None
    sequence: int
    observed_at_ms: int
    segments: tuple[SegmentUpdated, ...] = ()
    status: StreamStatus = "ready"
    status_history: tuple[TranscriptEvent, ...] = ()
    end_reason: EndReason | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TranscriptValidationError("invalid_transition", message)


class TranscriptAccumulator:
    """Apply normalized events atomically; each accepted state is immutable.

    Single writer only. A new session/reconnection needs a fresh instance.
    The latest segment version replaces its predecessor without appending text.
    """

    def __init__(self) -> None:
        self._state: TranscriptState | None = None

    @property
    def state(self) -> TranscriptState | None:
        return self._state

    def apply(self, event: TranscriptEvent) -> TranscriptState:
        validate_event(event)
        previous = self._state
        payload = event.payload
        if previous is None:
            _require(isinstance(payload, StreamStarted), "A stream must begin with a start event")
            _require(event.sequence == 0 and event.observed_at_ms == 0,
                     "A stream must start at sequence and observation offset zero")
            result = TranscriptState(event.session_id, event.stream_id, event.provenance,
                                     payload.started_at, event.sequence, event.observed_at_ms)
        else:
            _require(previous.end_reason is None, "The stream is closed")
            _require((event.session_id, event.stream_id, event.provenance) ==
                     (previous.session_id, previous.stream_id, previous.provenance),
                     "Stream identity and provenance must remain constant")
            _require(event.sequence == previous.sequence + 1, "Expected the next normalized sequence")
            _require(event.observed_at_ms >= previous.observed_at_ms,
                     "Observation offsets cannot decrease")
            _require(not isinstance(payload, StreamStarted), "A stream cannot restart")
            if previous.status == "failed":
                _require(isinstance(payload, StreamEnded) and payload.reason == "failed",
                         "A failed stream can only close as failed")
            result = replace(previous, sequence=event.sequence, observed_at_ms=event.observed_at_ms)
            if isinstance(payload, SegmentUpdated):
                result = replace(result, segments=self._update_segment(previous.segments, payload))
            elif isinstance(payload, StreamStatusChanged):
                result = replace(result, status=payload.status,
                                 status_history=previous.status_history + (event,))
            elif isinstance(payload, StreamEnded):
                result = replace(result, end_reason=payload.reason,
                                 status="failed" if payload.reason == "failed" else previous.status)
        # All validation precedes this assignment, including segment transitions.
        self._state = result
        return result

    @staticmethod
    def _update_segment(segments: tuple[SegmentUpdated, ...], update: SegmentUpdated
                        ) -> tuple[SegmentUpdated, ...]:
        index = next((i for i, segment in enumerate(segments)
                      if segment.segment_id == update.segment_id), None)
        if index is None:
            _require(update.segment_index == len(segments) and update.revision == 1,
                     "New segments require the next index and revision one")
            return segments + (update,)
        previous = segments[index]
        _require(update.segment_index == index, "A segment index cannot change")
        _require(update.revision == previous.revision + 1, "Expected the next normalized revision")
        _require(previous.status != "final" or update.status == "final",
                 "A final segment cannot become partial")
        return segments[:index] + (update,) + segments[index + 1:]

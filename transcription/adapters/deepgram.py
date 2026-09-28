"""Normalize sanitized Deepgram live messages into ``TranscriptEvent`` 1.0.

The adapter deliberately accepts plain dictionaries so provider SDK callback
types never cross the adapter boundary. It owns all internal counters and IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Literal
from uuid import uuid4

from transcription.model import (
    SCHEMA_VERSION,
    Provenance,
    SegmentUpdated,
    StreamEnded,
    StreamStarted,
    StreamStatusChanged,
    TranscriptEvent,
)
from transcription.stream import TranscriptAccumulator


PROVIDER = "deepgram-nova-3"
_NO_OP_TYPES = frozenset({"Metadata", "SpeechStarted", "UtteranceEnd"})
_RESULT_BOUNDARY_TOLERANCE_MS = 1


class DeepgramAdapterError(ValueError):
    """Content-free adapter diagnostic safe to expose without transcript text."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _Word:
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class _ActiveSegment:
    segment_id: str
    segment_index: int
    revision: int
    text: str
    start_ms: int
    end_ms: int
    words: tuple[_Word, ...]


@dataclass(frozen=True)
class _Result:
    text: str
    start_ms: int
    end_ms: int
    is_final: bool
    words: tuple[_Word, ...]


def _error(code: str = "invalid_provider_message") -> DeepgramAdapterError:
    messages = {
        "invalid_provider_message": "Deepgram message has an unsupported shape",
        "invalid_result_timing": "Deepgram result has invalid timing",
        "invalid_result_finality": "Deepgram result has invalid finality",
        "invalid_result_channel": "Deepgram result has an invalid channel",
        "invalid_result_alternatives": (
            "Deepgram result has invalid alternatives"
        ),
        "invalid_result_transcript": "Deepgram result has invalid text",
        "invalid_transition": "Deepgram message contradicts the active segment",
        "observation_before_result": (
            "Deepgram result ends after its observation time"
        ),
        "result_overlaps_final": (
            "Deepgram result substantially overlaps finalized audio"
        ),
        "shorter_final_incompatible": (
            "Shorter Deepgram final cannot be normalized from available timing"
        ),
        "stream_closed": "Deepgram stream is already closed",
    }
    return DeepgramAdapterError(code, messages[code])


def _counter(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _error()
    return value


def _seconds(
    value: object,
    *,
    error_code: str = "invalid_provider_message",
) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or value < 0):
        raise _error(error_code)
    return float(value)


def _milliseconds(
    value: object,
    *,
    error_code: str = "invalid_provider_message",
) -> int:
    return int(round(_seconds(value, error_code=error_code) * 1000))


def _parse_words(value: object, result_start_ms: int, result_end_ms: int
                 ) -> tuple[_Word, ...]:
    # Word objects are optional alignment hints. A valid result-level transcript
    # must not be discarded because one hint is absent or internally noisy.
    if not isinstance(value, list):
        return ()
    words: list[_Word] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        text = raw.get("punctuated_word")
        if not isinstance(text, str) or not text:
            text = raw.get("word")
        if not isinstance(text, str) or not text:
            continue
        try:
            start_ms = _milliseconds(raw.get("start"))
            end_ms = _milliseconds(raw.get("end"))
        except DeepgramAdapterError:
            continue
        if start_ms > end_ms:
            continue
        # Result timing remains authoritative. Clipping also absorbs provider
        # float rounding and provisional word ranges that straddle the result.
        start_ms = max(start_ms, result_start_ms)
        end_ms = min(end_ms, result_end_ms)
        if start_ms >= end_ms:
            continue
        words.append(_Word(text=text, start_ms=start_ms, end_ms=end_ms))
    return tuple(words)


def _parse_result(message: dict[str, object]) -> _Result | None:
    start_seconds = _seconds(
        message.get("start"), error_code="invalid_result_timing")
    duration_seconds = _seconds(
        message.get("duration"), error_code="invalid_result_timing")
    start_ms = _milliseconds(
        start_seconds, error_code="invalid_result_timing")
    end_ms = _milliseconds(
        start_seconds + duration_seconds,
        error_code="invalid_result_timing",
    )
    is_final = message.get("is_final")
    if not isinstance(is_final, bool):
        raise _error("invalid_result_finality")
    channel = message.get("channel")
    if not isinstance(channel, dict):
        raise _error("invalid_result_channel")
    alternatives = channel.get("alternatives")
    if not isinstance(alternatives, list):
        raise _error("invalid_result_alternatives")
    if not alternatives:
        return None
    alternative = alternatives[0]
    if not isinstance(alternative, dict):
        raise _error("invalid_result_alternatives")
    text = alternative.get("transcript")
    if not isinstance(text, str):
        raise _error("invalid_result_transcript")
    words = _parse_words(alternative.get("words", []), start_ms, end_ms)
    return _Result(text=text, start_ms=start_ms, end_ms=end_ms,
                   is_final=is_final, words=words)


class DeepgramAdapter:
    """One Deepgram WebSocket mapped to one fresh transcript accumulator."""

    def __init__(
        self,
        *,
        session_id: str,
        source_id: str,
        started_at: datetime | None,
        stream_id: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.source_id = source_id
        self.stream_id = stream_id or f"deepgram-{uuid4().hex}"
        self.provenance = Provenance(
            origin="transcriber",
            delivery="live",
            source_id=source_id,
            provider=PROVIDER,
        )
        self.accumulator = TranscriptAccumulator()
        self._sequence = -1
        self._active: _ActiveSegment | None = None
        self._next_segment_index = 0
        self._last_final_end_ms: int | None = None
        self.start_event = self._emit(StreamStarted(started_at), observed_at_ms=0)

    def _emit(self, payload, *, observed_at_ms: int) -> TranscriptEvent:
        observed_at_ms = _counter(observed_at_ms)
        event = TranscriptEvent(
            schema_version=SCHEMA_VERSION,
            session_id=self.session_id,
            stream_id=self.stream_id,
            sequence=self._sequence + 1,
            observed_at_ms=observed_at_ms,
            provenance=self.provenance,
            payload=payload,
        )
        self.accumulator.apply(event)
        self._sequence = event.sequence
        return event

    def _ensure_open(self) -> None:
        state = self.accumulator.state
        if state is None or state.end_reason is not None:
            raise _error("stream_closed")

    def _segment_update(
        self,
        *,
        segment_id: str,
        segment_index: int,
        revision: int,
        status: Literal["partial", "final"],
        text: str,
        start_ms: int,
        end_ms: int,
        observed_at_ms: int,
    ) -> TranscriptEvent:
        if end_ms > observed_at_ms:
            raise _error("observation_before_result")
        return self._emit(SegmentUpdated(
            segment_id=segment_id,
            segment_index=segment_index,
            revision=revision,
            status=status,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
            speaker_id=None,
        ), observed_at_ms=observed_at_ms)

    def _open_segment(self, result: _Result, observed_at_ms: int) -> TranscriptEvent:
        if (self._last_final_end_ms is not None
                and result.start_ms < self._last_final_end_ms):
            overlap_ms = self._last_final_end_ms - result.start_ms
            if overlap_ms > _RESULT_BOUNDARY_TOLERANCE_MS:
                raise _error("result_overlaps_final")
            boundary = self._last_final_end_ms
            result = _Result(
                text=result.text,
                start_ms=boundary,
                end_ms=result.end_ms,
                is_final=result.is_final,
                words=tuple(
                    _Word(
                        text=word.text,
                        start_ms=max(word.start_ms, boundary),
                        end_ms=word.end_ms,
                    )
                    for word in result.words
                    if word.end_ms > boundary
                ),
            )
        index = self._next_segment_index
        segment_id = f"{self.stream_id}:segment:{index}"
        event = self._segment_update(
            segment_id=segment_id,
            segment_index=index,
            revision=1,
            status="final" if result.is_final else "partial",
            text=result.text,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
            observed_at_ms=observed_at_ms,
        )
        self._next_segment_index += 1
        if result.is_final:
            self._last_final_end_ms = result.end_ms
        else:
            self._active = _ActiveSegment(
                segment_id, index, 1, result.text, result.start_ms,
                result.end_ms, result.words,
            )
        return event

    def _shorter_final(self, result: _Result, observed_at_ms: int
                      ) -> tuple[TranscriptEvent, TranscriptEvent]:
        active = self._active
        if active is None:
            raise _error("invalid_transition")
        remainder_words = tuple(
            _Word(
                text=word.text,
                start_ms=max(word.start_ms, result.end_ms),
                end_ms=word.end_ms,
            )
            for word in active.words
            if word.end_ms > result.end_ms
        )
        if not remainder_words or not all(word.text for word in remainder_words):
            raise _error("shorter_final_incompatible")
        remainder_text = " ".join(word.text for word in remainder_words)

        settled = self._segment_update(
            segment_id=active.segment_id,
            segment_index=active.segment_index,
            revision=active.revision + 1,
            status="final",
            text=result.text,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
            observed_at_ms=observed_at_ms,
        )
        self._last_final_end_ms = result.end_ms

        remainder_index = self._next_segment_index
        remainder_id = f"{self.stream_id}:segment:{remainder_index}"
        remainder = self._segment_update(
            segment_id=remainder_id,
            segment_index=remainder_index,
            revision=1,
            status="partial",
            text=remainder_text,
            start_ms=result.end_ms,
            end_ms=active.end_ms,
            observed_at_ms=observed_at_ms,
        )
        self._next_segment_index += 1
        self._active = _ActiveSegment(
            remainder_id,
            remainder_index,
            1,
            remainder_text,
            result.end_ms,
            active.end_ms,
            remainder_words,
        )
        return settled, remainder

    def accept(self, message: object, *, observed_at_ms: int
              ) -> tuple[TranscriptEvent, ...]:
        """Normalize one callback without exposing the provider object downstream."""
        self._ensure_open()
        observed_at_ms = _counter(observed_at_ms)
        if not isinstance(message, dict):
            raise _error()
        message_type = message.get("type")
        if message_type in _NO_OP_TYPES:
            return ()
        if message_type != "Results":
            raise _error()
        result = _parse_result(message)
        if result is None:
            return ()
        if result.text == "" and not result.words:
            return ()

        active = self._active
        if active is None:
            return (self._open_segment(result, observed_at_ms),)
        # Deepgram exposes one current unfinalized window. Every subsequent
        # interim replaces that provisional window, including its range; the
        # provider start offset is not segment identity.
        if result.is_final and result.end_ms < active.end_ms:
            has_timed_remainder = any(
                word.end_ms > result.end_ms for word in active.words)
            if not active.words or has_timed_remainder:
                return self._shorter_final(result, observed_at_ms)

        event = self._segment_update(
            segment_id=active.segment_id,
            segment_index=active.segment_index,
            revision=active.revision + 1,
            status="final" if result.is_final else "partial",
            text=result.text,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
            observed_at_ms=observed_at_ms,
        )
        if result.is_final:
            self._active = None
            self._last_final_end_ms = result.end_ms
        else:
            self._active = _ActiveSegment(
                active.segment_id,
                active.segment_index,
                active.revision + 1,
                result.text,
                result.start_ms,
                result.end_ms,
                result.words,
            )
        return (event,)

    def fail(self, *, observed_at_ms: int, code: str) -> tuple[TranscriptEvent, TranscriptEvent]:
        """Record provider/transport failure without retaining its private details."""
        self._ensure_open()
        if not isinstance(code, str) or not code.strip():
            raise _error()
        failed = self._emit(StreamStatusChanged("failed"), observed_at_ms=observed_at_ms)
        ended = self._emit(StreamEnded("failed"), observed_at_ms=observed_at_ms)
        return failed, ended

    def close(self, *, observed_at_ms: int,
              reason: Literal["completed", "cancelled"] = "completed") -> TranscriptEvent:
        self._ensure_open()
        if reason not in ("completed", "cancelled"):
            raise _error()
        return self._emit(StreamEnded(reason), observed_at_ms=observed_at_ms)

    def reconnect(self, *, started_at: datetime | None) -> "DeepgramAdapter":
        """Start a new WebSocket boundary with a new ID and accumulator."""
        state = self.accumulator.state
        if state is None or state.end_reason is None:
            raise _error("invalid_transition")
        return type(self)(
            session_id=self.session_id,
            source_id=self.source_id,
            started_at=started_at,
        )

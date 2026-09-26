"""Immediate, ordered replay of normalized events, without clocks or I/O services."""
from collections.abc import Iterable, Iterator
from dataclasses import replace
from pathlib import Path

from transcription.model import (
    TranscriptEvent, TranscriptValidationError, _decode_json, event_from_dict, validate_event,
)
from transcription.stream import TranscriptAccumulator, TranscriptState


def _as_replay(event: TranscriptEvent) -> TranscriptEvent:
    validate_event(event)
    return replace(event, provenance=replace(event.provenance, delivery="replay"))


def load_replay(path: str | Path) -> Iterator[TranscriptEvent]:
    """Load a small UTF-8 JSON event array, preserving its recorded array order.

    File errors propagate to the caller. Schema errors contain no source content.
    This fixture reader is not a production recording store or streaming parser.
    """
    try:
        data = _decode_json(Path(path).read_text(encoding="utf-8"))
    except UnicodeError:
        raise TranscriptValidationError("invalid_event", "Replay must be UTF-8 JSON") from None
    if not isinstance(data, list):
        raise TranscriptValidationError("invalid_event", "Replay must contain a JSON event array")
    for item in data:
        yield _as_replay(event_from_dict(item))


def replay(events: Iterable[TranscriptEvent]) -> Iterator[TranscriptState]:
    """Yield immutable states through the same accumulator future adapters use.

    Exhaust the iterator to verify explicit closure. Prior yielded states remain
    valid observations if a later event fails; failure never implies completion.
    Each call owns fresh state. Origin is preserved, delivery becomes replay.
    """
    accumulator = TranscriptAccumulator()
    for event in events:
        yield accumulator.apply(_as_replay(event))
    if accumulator.state is None or accumulator.state.end_reason is None:
        raise TranscriptValidationError("incomplete_stream", "Replay ended without explicit stream closure")

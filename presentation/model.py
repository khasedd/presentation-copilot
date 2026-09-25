"""Immutable normalized snapshots. Local references require a snapshot ID.

Hashes describe represented content, not rendered or semantic equivalence.
No provider payload, authentication context or live session state belongs here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Literal

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class Provenance:
    provider: str
    source_document_id: str
    source_page_id: str | None = None
    source_object_id: str | None = None


@dataclass(frozen=True)
class SourceRevision:
    revision_id: str | None
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.fetched_at.tzinfo is None or self.fetched_at.utcoffset() is None:
            raise ValueError("fetched_at must be timezone-aware")


@dataclass(frozen=True)
class TableCell:
    row: int
    column: int
    row_span: int
    column_span: int
    text: str


@dataclass(frozen=True)
class SlideElement:
    id: str
    kind: Literal["shape", "group", "table", "word_art", "image", "chart", "video", "line", "unknown"]
    position: int
    provenance: Provenance
    text: str = ""
    alt_title: str | None = None
    alt_description: str | None = None
    children: tuple[SlideElement, ...] = ()
    table_cells: tuple[TableCell, ...] = ()
    table_rows: int | None = None
    table_columns: int | None = None
    extraction_status: Literal["complete", "partial", "unsupported"] = "complete"


@dataclass(frozen=True)
class SpeakerNotes:
    text: str
    status: Literal["present", "empty", "unavailable"]
    provenance: Provenance


@dataclass(frozen=True)
class Concept:
    """Reserved for later derivation; the v1 ingestion path emits none."""
    id: str
    text: str
    support_refs: tuple[str, ...]
    derivation_method: str
    confidence: float | None = None


@dataclass(frozen=True)
class Slide:
    id: str
    position: int
    provenance: Provenance
    elements: tuple[SlideElement, ...]
    speaker_notes: SpeakerNotes
    content_fingerprint: str
    concepts: tuple[Concept, ...] = ()
    concept_status: Literal["not_extracted"] = "not_extracted"


@dataclass(frozen=True)
class NormalizationIssue:
    code: str
    reference: str
    message: str


@dataclass(frozen=True)
class Deck:
    schema_version: str
    snapshot_id: str
    title: str
    provenance: Provenance
    source_revision: SourceRevision
    slides: tuple[Slide, ...]
    issues: tuple[NormalizationIssue, ...] = ()


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _content(value: object) -> object:
    """Remove references/positions, retaining array order and represented content."""
    if isinstance(value, dict):
        return {key: _content(item) for key, item in value.items()
                if key not in {"id", "position", "provenance", "content_fingerprint", "concepts", "concept_status"}}
    if isinstance(value, (tuple, list)):
        return [_content(item) for item in value]
    return value


def slide_fingerprint(slide: Slide) -> str:
    return _digest({"schema_version": SCHEMA_VERSION, "content": _content(asdict(slide))})


def _snapshot_digest(deck: Deck) -> str:
    # Issues and observation metadata are not source content. Derived concepts
    # do not change the imported snapshot; their eventual lifecycle is separate.
    slides = []
    for slide in deck.slides:
        data = asdict(slide)
        data.pop("concepts")
        data.pop("concept_status")
        slides.append(data)
    return _digest({"schema_version": deck.schema_version, "title": deck.title,
                    "provenance": asdict(deck.provenance), "slides": slides})


def finalize_deck(deck: Deck) -> Deck:
    deck = replace(deck, slides=tuple(replace(slide, content_fingerprint=slide_fingerprint(slide))
                                     for slide in deck.slides))
    deck = replace(deck, snapshot_id=_snapshot_digest(deck))
    validate_deck(deck)
    return deck


def walk_elements(elements: tuple[SlideElement, ...]):
    for element in elements:
        yield element
        yield from walk_elements(element.children)


def has_substantive_text(slide: Slide) -> bool:
    return bool(slide.speaker_notes.text.strip() or any(
        element.text.strip() or any(cell.text.strip() for cell in element.table_cells)
        for element in walk_elements(slide.elements)))


def extraction_complete(slide: Slide) -> bool:
    """Complete only for the documented normalized subset, never visual fidelity."""
    return (slide.speaker_notes.status != "unavailable" and
            all(element.extraction_status == "complete" for element in walk_elements(slide.elements)))


def slide_provenance(slide: Slide) -> tuple[Provenance, ...]:
    return (slide.provenance, slide.speaker_notes.provenance,
            *(element.provenance for element in walk_elements(slide.elements)))


def validate_deck(deck: Deck) -> None:
    """Validate internal references, order and fingerprints before consumption."""
    if deck.schema_version != SCHEMA_VERSION:
        raise ValueError("Unsupported representation schema")
    source = (deck.provenance.provider, deck.provenance.source_document_id)
    if not all(source):
        raise ValueError("Source provenance is required")
    local_refs: set[str] = {"deck"}
    page_ids: set[str] = set()

    def elements_valid(elements: tuple[SlideElement, ...], parent: str) -> None:
        for position, element in enumerate(elements):
            if element.position != position or element.id != f"{parent}/element/{position}":
                raise ValueError("Invalid element order/reference")
            local_refs.add(element.id)
            elements_valid(element.children, element.id)

    for position, slide in enumerate(deck.slides):
        if slide.position != position or slide.id != f"slide/{position}":
            raise ValueError("Invalid slide order/reference")
        if slide.provenance.source_page_id is not None:
            if slide.provenance.source_page_id in page_ids:
                raise ValueError("Duplicate source slide ID")
            page_ids.add(slide.provenance.source_page_id)
        local_refs.update((slide.id, slide.id + "/notes"))
        elements_valid(slide.elements, slide.id)
        if any((p.provider, p.source_document_id) != source for p in slide_provenance(slide)):
            raise ValueError("Inconsistent source provenance")
        if slide.concepts or slide.concept_status != "not_extracted":
            raise ValueError("Concept derivation is not implemented in schema 1.0 ingestion")
        if slide.content_fingerprint != slide_fingerprint(slide):
            raise ValueError("Invalid slide fingerprint")
    if any(issue.reference not in local_refs for issue in deck.issues):
        raise ValueError("Issue references an unknown object")
    if deck.snapshot_id != _snapshot_digest(deck):
        raise ValueError("Invalid snapshot digest")


def deck_to_json(deck: Deck) -> str:
    validate_deck(deck)
    data = asdict(deck)
    data["source_revision"]["fetched_at"] = deck.source_revision.fetched_at.isoformat()
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"

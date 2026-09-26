"""Conservative two-snapshot comparison, without persistent identity or state."""
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from presentation.model import (
    Deck, Slide, extraction_complete, has_substantive_text,
    slide_provenance, validate_deck,
)


@dataclass(frozen=True)
class SlideMatch:
    previous_id: str
    current_id: str
    previous_position: int
    current_position: int
    basis: Literal["source_id", "content_fingerprint"]
    content_changed: bool
    provenance_changed: bool
    reuse: Literal["eligible", "invalidate", "rebind_required", "review_required"]


@dataclass(frozen=True)
class AmbiguousMatch:
    previous_ids: tuple[str, ...]
    current_ids: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotComparison:
    previous_snapshot_id: str
    current_snapshot_id: str
    matches: tuple[SlideMatch, ...]
    order_changed: bool
    added: tuple[str, ...]
    removed: tuple[str, ...]
    ambiguous: tuple[AmbiguousMatch, ...]
    issues: tuple[str, ...]


def _match(old: Slide, new: Slide, basis: str) -> SlideMatch:
    changed = old.content_fingerprint != new.content_fingerprint
    provenance_changed = slide_provenance(old) != slide_provenance(new)
    if changed:
        reuse = "invalidate"
    elif not extraction_complete(old) or not extraction_complete(new):
        reuse = "review_required"
    elif provenance_changed:
        reuse = "rebind_required"
    else:
        reuse = "eligible"
    return SlideMatch(old.id, new.id, old.position, new.position, basis,
                      changed, provenance_changed, reuse)


def compare_snapshots(previous: Deck, current: Deck) -> SnapshotComparison:
    """Match source IDs first, then unique substantive content among unmatched slides.

    Reuse labels apply only to concepts derived from the normalized subset.
    They never permit carrying forward live coverage or assuming visual equality.
    """
    validate_deck(previous)
    validate_deck(current)
    if previous.provenance != current.provenance:
        raise ValueError("Snapshots must belong to the same provider and source document")
    remaining_old = {slide.id: slide for slide in previous.slides}
    remaining_new = {slide.id: slide for slide in current.slides}
    new_by_source = {slide.provenance.source_page_id: slide for slide in current.slides
                     if slide.provenance.source_page_id is not None}
    matches = []
    for old in previous.slides:
        new = new_by_source.get(old.provenance.source_page_id)
        if new is not None:
            matches.append(_match(old, new, "source_id"))
            del remaining_old[old.id]
            del remaining_new[new.id]

    def by_content(slides):
        groups = defaultdict(list)
        for slide in slides:
            if has_substantive_text(slide):
                groups[slide.content_fingerprint].append(slide)
        return groups

    old_groups = by_content(remaining_old.values())
    new_groups = by_content(remaining_new.values())
    ambiguous = []
    for fingerprint, old_candidates in old_groups.items():
        new_candidates = new_groups.get(fingerprint, [])
        if not new_candidates:
            continue
        if len(old_candidates) == len(new_candidates) == 1:
            matches.append(_match(old_candidates[0], new_candidates[0], "content_fingerprint"))
        else:
            ambiguous.append(AmbiguousMatch(tuple(s.id for s in old_candidates),
                                            tuple(s.id for s in new_candidates)))
        for old in old_candidates:
            del remaining_old[old.id]
        for new in new_candidates:
            del remaining_new[new.id]

    matches.sort(key=lambda match: match.previous_position)
    current_positions = [match.current_position for match in matches]
    issues = []
    if previous.issues or current.issues:
        issues.append("Comparison covers normalized content only; inspect both snapshots' extraction issues.")
    if ambiguous:
        issues.append("Duplicate content prevents deterministic correspondence; no reuse is authorized.")
    return SnapshotComparison(previous.snapshot_id, current.snapshot_id, tuple(matches),
                              current_positions != sorted(current_positions),
                              tuple(remaining_new), tuple(remaining_old), tuple(ambiguous), tuple(issues))

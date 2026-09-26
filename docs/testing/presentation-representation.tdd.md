# Phase 2 foundation — test evidence

The owner-approved conversation supplied the scope and journeys; no external plan file was used. Journeys: ingest a presentation without coupling consumers to Google; retain content/notes/provenance; distinguish reordered and changed slides without inventing permanent identity; fail safely on invalid or interrupted input.

## RED / GREEN record

- Baseline: `python3 -m unittest discover -s tests -v` — 11 existing tests passed.
- `7d5eaa2`: new representation, adapter and comparison tests added. Discovery reported three import errors because the intended `presentation` package did not exist, while the 11 original tests passed.
- `8679771`: implementation added. The same command passed all 35 tests, including mocked HTTP-to-CLI serialization.
- `6099ba6`: structural edge cases and interrupted-body regression added. `python3 -m unittest discover -s tests -p test_google_slides.py` ran 15 tests: 14 passed and one errored with uncaught `http.client.IncompleteRead`.
- `987216f`: translated interrupted HTTP responses into sanitized transport errors. Full discovery passed all **41 tests** (30 new, 11 existing).

## Guarantees and limits

| Guarantee | Test location | Verification |
| --- | --- | --- |
| Versioned JSON preserves source IDs, order, notes/revision metadata and local references | `tests/test_presentation_model.py` | PASS |
| Snapshot hashes ignore observation time/token changes; slide hashes exclude IDs/position | `tests/test_presentation_model.py` | PASS |
| Unicode/run text, groups, tables/merged cells, designated notes and unsupported markers survive normalization | `tests/test_google_slides.py` | PASS, synthetic fixture |
| Malformed structure, table holes/overlaps, unknown text and missing notes are handled explicitly | `tests/test_google_slides.py` | PASS |
| Reorders differ from insertion/deletion shifts; notes/content changes invalidate reuse | `tests/test_presentation_comparison.py` | PASS |
| Replacement IDs require rebinding; duplicate content stays ambiguous; blank/visual-only slides do not fingerprint-match | `tests/test_presentation_comparison.py` | PASS |
| Authentication/access/network/interrupted-body errors are sanitized; redirects and oversized responses fail | `tests/test_google_slides.py` | PASS, mocked transport |
| CLI ingests through adapter and writes JSON without printing content/token or overwriting output | `tests/test_google_slides.py` | PASS, offline CLI integration |
| Existing semantic experiments retain behavior | Existing two test modules | 11 tests PASS |

`python3 -m py_compile` was run on the five new functional modules and `python3 -m experiments.ingest_google_slides --help` was exercised. These are supplemental checks, not behavioral proof.

## Coverage

The environment has no `coverage` package; none was added as a project dependency. Python standard-library tracing was run instead:

```bash
python3 -m trace --count --summary --missing --coverdir /tmp/copilot-phase2-coverage --module unittest discover -s tests
```

| New module | Trace line coverage |
| --- | ---: |
| `presentation.model` | 95.6% |
| `presentation.source` | 90.9% |
| `presentation.comparison` | 100.0% |
| `presentation.adapters.google_slides` | 98.6% |
| `experiments.ingest_google_slides` | 96.9% |

These are standard-library trace line measurements, not branch coverage or a claim of exhaustive correctness. No browser test applies to this CLI-only foundation. Remaining gaps include visual semantics, large realistic decks, full persistent identity and group-inside-group live content.

## Live baseline evidence — September 25, 2026

The owner authorized read-only ingestion of an eight-slide fixture. `python3 presentation-output/verify_baseline.py` loaded only `GOOGLE_SLIDES_ACCESS_TOKEN` from the ignored local `.env` and invoked `python3 -m experiments.ingest_google_slides <owner-supplied-id> --output <ignored-baseline-path>`. An initial sandboxed attempt returned a sanitized transport error; the network-enabled attempt succeeded. The normalized snapshot was observed at `2026-09-25T19:45:08.593763+00:00`.

- **189 independent field assertions passed** against a second read-only source response: presentation provenance, eight ordered slide IDs, direct text, notes, table dimensions/cell coordinates/spans/text, image provenance/alt text and group children.
- Re-normalizing the captured source with the baseline observation timestamp reproduces the saved JSON exactly. Revision metadata was present and matched across the two source reads.
- A 2×3 table retains six cells at `(0,0)` through `(1,2)`. Notes are nonempty on two slides. The sparse slide retains one element and empty notes.
- The fixture has one group with two empty-text shape children. Child hierarchy/IDs are verified; no group-inside-group case exists in this live source.
- Slides 7 and 8 have equal fingerprints but different source IDs. Baseline self-comparison produces eight unchanged source-ID matches and zero ambiguous matches. Content-only matching of the duplicate pair is non-unique; the earlier synthetic ambiguity regression remains the fallback-behavior evidence. No live mutation/reorder test was performed.
- Exactly two expected extraction notices were emitted: normalized-subset limitations and unsupported raster-image semantics.
- Snapshot/source/report files are ignored and mode `0600`. No source mutation occurred and no credential or raw live content is committed.

The initial live-ingestion portion passed before the owner's separate approval for mutation/reorder testing below.

## Live mutation/reorder evidence

The owner approved a controlled mutation pass. A preflight initially received HTTP 401 and made no changes. After the owner refreshed the local token, preflight confirmed the current normalized deck still matched the saved baseline. The verification scripts read only the Slides credential from ignored `.env`; mutation support exists only in the private test harness, not in the application's read-only adapter.

Commands from the repository root:

```bash
python3 presentation-output/phase2_mutation_check.py prepare
python3 presentation-output/phase2_mutation_check.py mutate
python3 presentation-output/phase2_mutation_check.py verify
python3 -m unittest discover -s tests -v
```

The title slide was duplicated first. Its normalized fingerprint matched before the original was deleted. The content/add/remove batch was followed by a structural readback and a separate reorder request. Each batch carried `writeControl.requiredRevisionId`. Requests, responses, intermediate source observations, the second normalized snapshot and reports remain in ignored owner-only files. No raw live content or credentials are committed.

The second snapshot was fetched at `2026-09-26T00:06:58.651772+00:00`. A separate source read normalized to exactly the same JSON. Snapshot comparison used a reconstruction of the baseline source at its original timestamp, asserted structurally identical after JSON parsing to the saved baseline before comparison.

| Controlled change / retained slide | Old → new position (one-based) | Match basis | Content changed | Provenance changed | Reuse recommendation |
| --- | --- | --- | --- | --- | --- |
| Original title replaced by verified duplicate | 1 → 1 | `content_fingerprint` | false | true | `rebind_required` |
| Visible body text prepended; source slide ID retained | 2 → 3 | `source_id` | true | false | `invalidate` |
| Notes text prepended; visible elements/source slide ID retained | 3 → 4 | `source_id` | true | false | `invalidate` |
| Table slide moved; content unchanged | 4 → 2 | `source_id` | false | false | `eligible` |
| Visual slide unchanged | 5 → 5 | `source_id` | false | false | `review_required` |
| Duplicate A unchanged | 7 → 6 | `source_id` | false | false | `eligible` |
| Duplicate B unchanged | 8 → 7 | `source_id` | false | false | `eligible` |

Exact remaining comparison fields: `order_changed=true`, `added=["slide/7"]` in the current snapshot, `removed=["slide/5"]` in the previous snapshot, and `ambiguous=[]`. Local IDs are zero-based; the new slide is eighth and the removed sparse slide was sixth. Seven matches comprise six source-ID matches and one fingerprint correspondence. The comparator emits its normalized-content-only limitation notice. `eligible` concerns concepts derived from the represented subset, never automatic coverage carryover.

The unchanged live duplicate pair correctly matches by source ID. A supplemental in-memory projection removed only their slide page-ID hints, leaving both saved live snapshots intact. This returned exactly one ambiguity group: previous `("slide/6", "slide/7")` versus current `("slide/5", "slide/6")`; neither candidate was position-matched. Add/remove results stayed the same. This is explicitly a simulation of missing ID evidence, not a claim that the live duplicate pair's IDs changed.

Both source revisions were present and different; the current revision matched the subsequent source read. Added text was unique and preserved, retained table/visual/duplicate fingerprints were unchanged, and text versus notes-only changes were checked independently. No live coverage state was created or carried forward. All generated Phase 2 artifacts are ignored and mode `0600`; an exact-value exclusion check confirmed the configured credential is absent from tracked files.

Final suite: **41 tests run, 41 passed, 0 failed**. No production code changes were required by the live verification. The Phase 2 exit gate passes. Remaining limits: supported normalized subset only, no visual understanding, no live group-inside-group fixture, no persistent identity, and duplicate fallback exercised in memory rather than by changing the preserved live pair. Semantic extraction and broader representative evaluation remain unchecked. The owner approved the verified foundation for integration through PR #4.

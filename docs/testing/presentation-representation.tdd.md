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

These are standard-library trace line measurements, not branch coverage or a claim of exhaustive correctness. No browser test applies to this CLI-only foundation. Remaining gaps include real OAuth/network access, source-checked representative ingestion, visual semantics, large realistic decks and full persistent identity. Live verification is explicitly pending owner-supplied presentation ID and local credentials; no live completion is claimed.

# Phase 3 transcript contract — test evidence

Verified September 26, 2026. The owner-approved conversation supplied the model, file plan, and journeys; no external plan file was used. Owner clarifications require adapter-owned normalized sequence/revision counters and deterministic UTC serialization of aware start datetimes.

Journeys: consume evolving speech without tying consumers to a provider; replace partial/final hypotheses safely; reject stale or cross-stream input without corrupting accepted state; preserve explicit uncertainty and failure; replay the same synthetic scenario into identical states without live audio or timing dependencies.

## RED / GREEN record

- Baseline: `python3 -m unittest discover -s tests -q` — **41 passed**.
- `e0ff162`: tests and synthetic fixture added before production code. `python3 -m unittest discover -s tests -v` reported **41 existing tests passing and two test-module import errors**, both because the intended `transcription` package did not exist. This is missing-implementation RED evidence, not individual assertions executing.
- Initial implementation run discovered a test-helper keyword collision (`payload` supplied twice). Renaming the helper's positional parameter enabled the intended malformed-payload assertion; no contract expectation was relaxed.
- `c240dc3`: implementation plus that helper correction. Full discovery ran **68 tests, all passing**.
- `b578073`: added six narrowly scoped tests after review. `python3 -m unittest discover -s tests -p 'test_transcript_*.py' -q` ran **33 tests, with two failing subcases**: the decoder accepted `+00:60` and unknown `-00:00` timestamp offsets.
- `ad5e016`: strict offset validation added. `python3 -m unittest discover -s tests -v` ran **74 tests, all passing** (41 existing, 33 new). The full suite also passed under the coverage run below.
- Executed the documented replay example independently: **Replayed 10 events; 2 segments**; its revision, unfinished-partial and closure assertions passed. Local documentation file links resolve, and `git diff --check` passed.

## Guarantees

| Guarantee | Test location | Type / result |
| --- | --- | --- |
| All four payloads round-trip; exact Unicode/whitespace retained; equivalent instants serialize identically in UTC | `tests/test_transcript_model.py` | Unit, PASS |
| Naive/invalid/unknown-offset timestamps, invalid counters, unknown schemas, malformed/extra/missing/duplicate JSON fields rejected | `tests/test_transcript_model.py` | Unit, PASS |
| Partial → corrected partial → final → corrected final replaces text and preserves earlier state snapshots | `tests/test_transcript_replay.py` | Transition, PASS |
| Interleaved revisions, overlapping audio and equal observation offsets preserve first-observed segment order | `tests/test_transcript_replay.py` | Transition, PASS |
| Duplicates, gaps, stale revisions, index changes, wrong sessions/streams/provenance and post-end events fail atomically | `tests/test_transcript_replay.py` | Transition, PASS |
| Missing/delayed history survives readiness; failed streams allow only failed closure; partials remain partial on end | `tests/test_transcript_replay.py` | Transition, PASS |
| Reconnection/new-session accumulators start empty and reject old-stream input | `tests/test_transcript_replay.py` | Transition, PASS |
| Ten-event fixture produces identical state sequences across repeated runs; origin survives replay relabeling | `tests/fixtures/transcript_evolution.json`, `tests/test_transcript_replay.py` | Fixture-to-state integration, PASS |
| Replay has no sleeping/network/wall-clock use; empty/truncated input and trailing events are detected | `tests/test_transcript_replay.py` | Integration, PASS; sleep/time/socket calls patched to fail |
| Bad UTF-8/JSON produces content-free errors; missing-file errors propagate | `tests/test_transcript_replay.py` | File integration, PASS |
| Phase 2 and isolated semantic experiment behavior remains passing | Complete repository discovery | Regression, PASS |

## Coverage

No third-party coverage package is installed or added. Python's standard-library `trace` measured line execution while discovering and running the full test suite. An initial measurement began after discovery/imports and understated coverage; the corrected command below traces discovery as well. Only the corrected measurement is used here.

```bash
python3 - <<'PY'
import sys
import trace
import unittest

def run_suite():
    return unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover('tests'))

tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.base_prefix])
result = tracer.runfunc(run_suite)
tracer.results().write_results(show_missing=True, summary=True, coverdir='/tmp/copilot-phase3-coverage')
raise SystemExit(not result.wasSuccessful())
PY
```

Observed on Python 3.14:

| New production module | Lines reported by `trace` | Line coverage |
| --- | ---: | ---: |
| `transcription/model.py` | 161 | 100.0% |
| `transcription/replay.py` | 24 | 100.0% |
| `transcription/stream.py` | 74 | 98.6% |

This measures line execution, including imports/class definitions; it is not branch coverage or a proof that every input combination is tested. The remaining reported stream line is the continuation of `_update_segment`'s function signature, not a missed behavior branch. The package initializer contains only a docstring. No browser/UI test is applicable because this slice exposes a Python library, not an application UI.

## Limits and review evidence

The synthetic fixture is the complete offline input path for this slice. It does not establish microphone permissions, transcription quality, measured latency, a live provider, actual speaker recognition, transport/backpressure behavior, privacy consent, or a live-transcription gate. A synthetic provider label tests provenance only; no provider call occurs.

The accumulator is single-writer and in-memory. Tests validate one stream per run, fresh state on reconnection, and rejection across boundaries; they do not implement full application session orchestration, global ID allocation, retained audio, split/merge corrections, or coverage integration. Replay callers must exhaust the iterator to check explicit closure.

The RED/GREEN checkpoint history above preserves the evidence if a later owner-authorized merge squashes commits. This slice is submitted for draft review, not merged, and does not complete the Phase 3 exit gate.

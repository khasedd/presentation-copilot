# Foundation completion verification — September 26, 2026

Source: the owner's request to finish unchecked Phase 0–2 work before further Phase 3 implementation. No external plan file was used. No subagents or new runtime dependencies were used.

## Journeys and guarantees

| Journey / guarantee | Test target | Evidence |
| --- | --- | --- |
| Derive reviewable concepts from direct text, nested groups, table cells and presenter notes without changing the source snapshot | `tests/test_concept_extraction.py` | Exact source quotes/references, snapshot ID, null confidence and review-required status asserted |
| Never turn an unsupported slide, provider failure, oversized input or invalid output into approved empty concepts | `tests/test_concept_extraction.py` | Distinct no-text/input-limit/failure states; invented references/quotes, duplicate fields/concepts and malformed shapes rejected |
| Treat embedded source instructions as data | `tests/test_concept_extraction.py` | Source JSON separated from system instructions; this does not prove immunity to model prompt injection |
| Measure candidate workloads without recording credentials or interpreting truncated output as usable | `tests/test_foundation_probe.py` | Bounded requests, sanitized 429/timeout/malformed failures, refusal/truncation rejection, allowlisted metadata |
| Preserve trial evidence and return failure when results are incorrect | `tests/test_foundation_probe.py` | Mocked end-to-end CLI, 27 recorded attempts, exclusive `0600` file, no key in output, missing-key failure before output |
| Include queue delay and competing jobs in a scheduled deadline | `tests/test_foundation_load.py` | Controlled clock produces a seven-second result from a three-second request plus four seconds queued; failed deadline remains failed |
| Preserve existing load evidence and report a missed deadline honestly | `tests/test_foundation_load.py` | CLI exit 1, no overwrite or second inference, owner-only output |

## RED/GREEN checkpoints

The existing suite passed **74 tests** before changes.

1. `python3 -m unittest discover -s tests -p test_concept_extraction.py -v` failed with the intended missing `presentation.concepts` module. RED commit: `0b0e678`. Implemented source-grounded drafts; `python3 -m unittest discover -s tests -q` passed **83 tests**. GREEN commit: `a5fcd0b`.
2. `python3 -m unittest discover -s tests -p test_foundation_probe.py -q` failed with the intended missing `experiments.foundation_probe` module. RED commit: `3c33cf8`. Implemented the bounded workload runner; the full suite passed **90 tests**. GREEN commit: `fcfa17c`.
3. Added CLI/resource verification; full suite passed **93 tests**. Then `python3 -m unittest discover -s tests -p test_foundation_load.py -q` failed with the intended missing load module. RED commit: `d21a0f9`. Implemented scheduled queue/deadline measurement; the full suite passed **95 tests**. GREEN commit: `6ed3cbc`.
4. Added load CLI evidence-preservation checks. Final full suite: **97 tests pass** (74 existing, 23 new).

These compile/import RED signals exercised newly specified missing interfaces, not unrelated test-setup or dependency failures. Checkpoints are preserved on `codex/close-foundation-gaps`; this report also preserves their evidence if a future merge squashes them.

## Coverage

Executed:

```bash
python3 -m trace --count --summary --missing \
  --coverdir /tmp/copilot-foundation-coverage \
  --module unittest discover -s tests -q
```

Python standard-library statement coverage for changed implementation modules:

| Module | Executable lines | Covered |
| --- | ---: | ---: |
| `presentation.concepts` | 83 | 97.6% |
| `experiments.foundation_probe` | 136 | 97.8% |
| `experiments.foundation_load` | 57 | 98.2% |

This is statement coverage, not branch coverage. Untested tails include module entry-point lines, interrupt handling and two defensive draft-budget/output checks. Real network behavior is measured separately below; mocked failure tests are not live-outage evidence.

## Live and manual evidence

- Official Devpost, Nebius and NVIDIA sources rechecked; source-format review cross-checked against current Google read-contract/user-data documentation. See the [foundation audit](../foundation-completion-audit.md).
- Authenticated model catalog still exposes the four expected NVIDIA routing keys. Console rate limits, provisioned credits and effective prices were inspected read-only; limits and credits were adequate for the experiments performed. No grants were redeemed, billing settings changed, or infrastructure provisioned.
- The live comparison completed **54 requests**. Super and Ultra passed 18/18 each; Nano passed 14/18. Exit **1** correctly records those failures.
- The scheduled Super trial completed **45 requests** with 45 correct outputs and **35/36** coverage deadlines met. Exit **1** correctly records the timing failure; the five-second target is not declared reliable.
- Eight tiny context-reservation probes preserve successful and rejected requests. The selected prompt succeeded with 20 prompt tokens plus a 262,124-token reservation and failed at 262,125. No full-length output or huge prompt was generated.
- Actual posted usage/billing was observed and remained minimal after the comparison/load trials. Nano/Ultra token usage reconciles to the recorded experiments; the complete Super account history is not reconstructed or falsely attributed to this task.

See [full measurements, raw synthetic results and limitations](../../experiments/FOUNDATION-TRIAL.md). Only repository-authored synthetic content went to inference. Existing private Google Slides artifacts remain ignored; no live deck mutation or Phase 3+ implementation was performed.

## Remaining uncertainty

Provider quota aggregation, the prompt-accounting discrepancy, independent full-context/output behavior, grant expiry/eligibility and production-scale reliability remain unverified. The owner explicitly requires unknown credit terms to remain unknown while the completed Phase 1 foundation and passed exit gate remain unchanged. These are non-blocking provider-operations follow-ups; no unsupported completion is fabricated to remove them.

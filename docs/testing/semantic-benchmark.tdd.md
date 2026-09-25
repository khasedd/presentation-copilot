# Semantic benchmark test evidence

Source: the user's Phase 1 task, with no external plan. Journey: compare the same four POC cases across all available NVIDIA models to identify a usable, efficient provisional choice without changing semantic behavior.

RED checkpoint `f4191cf`: `python3 -m unittest discover -s tests -v` failed because `experiments.semantic_benchmark` did not exist; the five original tests passed. GREEN checkpoint `625396b`: the same command passed all nine tests after implementation. The mocked case selector was corrected to use complete message equality because case C's transcript is a prefix of case D's. Two subsequent CLI tests bring the final suite to 11 passing tests.

| Guarantee | Evidence | Result |
| --- | --- | --- |
| All models receive the exact four POC messages three times with rotated order | `test_reuses_all_cases_messages_and_rotates_models` | PASS |
| Request/validation failures and semantic mismatches remain in the denominator and do not stop subsequent cases | `test_failures_are_counted_and_do_not_stop_other_cases` | PASS |
| Missing usage is unknown; invalid repeat counts are rejected | `test_missing_usage_is_unknown_and_invalid_repeat_rejected` | PASS |
| Original request payload, timeout, default model, and string return interface remain intact | `test_request_settings_and_original_string_interface_unchanged` | PASS |
| CLI writes a report, signals failed checks, and handles missing credentials | `test_cli_writes_report_and_returns_failure_for_failed_checks` | PASS |
| Original POC CLI still processes all four cases successfully | `test_original_poc_cli_still_evaluates_four_cases` | PASS (mocked transport) |
| Real provider integration across all four model IDs | `python3 -m experiments.semantic_benchmark --output experiments/results/semantic-benchmark-2026-09-16.json` | Completed 48 requests; 29 pass, 19 validation failures; exit 1 |

The five original contract tests also pass. No new runtime/test dependency was installed. `coverage` is unavailable, so line coverage was measured with the standard library:

```bash
python3 -m trace --count --summary --missing --coverdir /tmp/copilot-benchmark-coverage --module unittest discover -s tests
```

Result: 11 tests pass; benchmark module 94.6% (106/112 lines), existing POC module 79.5% (147/185 lines), combined 85.2% (253/297 lines). This is line coverage, not branch coverage. Existing provider HTTP/timeout error handling is not fully unit-tested; the benchmark's handling of the provider error type is tested. The live run had no transport failures. The four-case fixture remains too small for a realistic semantic-quality claim. See [the report](../../experiments/BENCHMARK.md) for the full method and interpretation.

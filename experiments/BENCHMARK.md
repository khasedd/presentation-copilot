# Phase 1: unchanged POC model benchmark

Run: September 16, 2026, 17:20:45–17:21:55 UTC (~70 seconds). Harness commit: `625396b`.

## Method

The authenticated Nebius Token Factory `/v1/models` endpoint returned the four NVIDIA IDs below. Each received the existing four A–D cases three times (48 requests). All calls reuse `evaluate_case`, `build_messages`, and `parse_coverage_result` from the POC. The slide, concepts, transcripts, expected statuses, prompts, JSON mode, temperature 0, 300-token cap, and 30-second timeout are unchanged. There are no reasoning overrides or model-specific prompt adjustments.

Requests run sequentially, interleaving models within each case and rotating their order between rounds. There are no retries, warmup exclusions, streaming, or concurrent load. Timing includes the complete client request, response parsing, and local validation; it is not time to first token or isolated inference time. Token totals are provider-reported prompt/completion usage across all 12 attempts, including failures. Missing usage is reported as unknown, not zero. No dollar cost or credit consumption is claimed: current account-specific pricing was not verified. Tokens are a resource measure, not a cross-model price comparison.

## Comparison

| Model | Passed | Errors | Mean s | Median s | Max s | Input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B | 11/12 | 1 | 1.969 | 2.034 | 2.213 | 3069 | 3245 |
| nvidia/Nemotron-3_5-Lightning | 0/12 | 12 | 1.686 | 1.673 | 1.941 | 3069 | 3600 |
| nvidia/nemotron-3-super-120b-a12b | 12/12 | 0 | 1.370 | 1.238 | 3.120 | 3069 | 2579 |
| nvidia/Nemotron-3-Ultra-550b-a55b | 6/12 | 6 | 0.810 | 0.828 | 0.905 | 3069 | 3345 |

| Model | A: paraphrase | B: keyword only | C: partial | D: complete |
| --- | ---: | ---: | ---: | ---: |
| Nano | 3/3 | 3/3 | 3/3 | 2/3 |
| Lightning | 0/3 | 0/3 | 0/3 | 0/3 |
| Super | 3/3 | 3/3 | 3/3 | 3/3 |
| Ultra | 0/3 | 0/3 | 3/3 | 3/3 |

All 19 failures were invalid coverage outputs with provider `finish_reason: length` at 300 completion tokens. There were no request failures and no schema-valid semantic mismatches. The harness retains validated results, usage, finish reason, duration, and outcome per attempt in [the JSON report](results/semantic-benchmark-2026-09-16.json). It does not retain raw invalid content or hidden reasoning, so the record establishes token-limit termination rather than the exact incomplete response structure.

## Decision and limits

**Keep Super as the provisional semantic-coverage model for this unchanged POC.** It was the only model with 12/12 usable correct responses, averaged 1.370 seconds per request, and used the fewest completion tokens (2,579). Nano was slower and failed once. Ultra's 0.810-second average was fastest, but half its outputs were unusable. Lightning hit the cap every time.

This measures suitability under the current request budget, not the intrinsic intelligence of the models. Raising the cap or changing reasoning settings might change the ranking, but doing so is outside this behavior-preserving comparison. Four simple synthetic cases repeated three times do not establish realistic presentation accuracy or production readiness. The measured ~1.2-second median for Super is an initial reference for checklist experiments, not an accepted live latency target. Broader speech, ambiguity, correction, and false-coverage evaluation remains required; automatic advancement remains unvalidated.

The existing substantive path remains NVIDIA inference through Nebius Token Factory; no new service, SDK, model hosting path, or dependency was introduced. This is not a new licensing/compliance certification or a completed Phase 1 exit gate. Nebius's [Nemotron guide](https://nebius.com/services/token-factory/nemotron) documents the provider/model path; the authenticated catalog, rather than marketing family names, supplied the exact tested IDs. The [official Nebius comparison cookbook](https://dev.nebius.com/cookbook/agent-cost-benchmark) provides useful broader context, but none of its measurements or price assumptions is used in this result.

## Reproduce

From the repository root, with the existing `NEBIUS_API_KEY` environment setting or ignored `.env`:

```bash
python3 -m experiments.semantic_benchmark --repeats 3 --output /tmp/semantic-benchmark.json
python3 -m unittest discover -s tests -v
```

The benchmark exits 0 only if every attempt matches, 1 if any attempt fails, and 2 for missing credentials or invalid CLI arguments. The recorded live run exited 1 as expected from its 19 validation failures. The original `python3 experiments/semantic_coverage.py` command and default Super model are preserved.

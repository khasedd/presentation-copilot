# Semantic-coverage proof of concept

`semantic_coverage.py` is the first isolated experiment for Presentation Copilot's core question: given one slide's required concepts and what a presenter said, which concepts were semantically covered?

It is intentionally not application architecture. It has no presentation ingestion, live transcription, UI, state store, automatic advancement, or production reliability layer.

## Selected model

The experiment uses `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory. Nebius currently documents this exact model identifier, an OpenAI-compatible API path, and its suitability for complex reasoning and instruction following in its [Nemotron + Token Factory guide](https://nebius.com/services/token-factory/nemotron). Its [model announcement](https://nebius.com/blog/posts/nemotron3-super-now-available) confirms current Token Factory availability.

This is a pragmatic first choice for structured semantic classification: it meets the hackathon's substantive Nebius/NVIDIA requirement and should reason over paraphrases better than a keyword matcher. It is not a final selection; Nano, Super, and Ultra variants still require workload-specific latency, quality, throughput, and cost investigation.

## Run it

Set `NEBIUS_API_KEY` in the environment, or keep it in the ignored local `.env` file. The script reads only that setting as data and never logs or writes its value.

```bash
python3 experiments/semantic_coverage.py
```

The script uses only the Python standard library. It sends each hardcoded case to Nebius Token Factory with JSON-object response mode, then rejects any response that does not contain exactly the supplied concept IDs, only `covered`/`not_covered` statuses, and a logically consistent `slide_complete` value.

## Verified live results

Run on September 14, 2026 with the selected model and the fixed **Transformer Basics** concepts:

| Case | Returned statuses (concepts 1–3) | `slide_complete` | Matched expected behavior |
| --- | --- | --- | --- |
| A — paraphrased coverage | `covered`, `not_covered`, `not_covered` | `false` | Yes |
| B — keyword only | `not_covered`, `not_covered`, `not_covered` | `false` | Yes |
| C — partial coverage | `covered`, `covered`, `not_covered` | `false` | Yes |
| D — complete coverage | `covered`, `covered`, `covered` | `true` | Yes |

Case A used the paraphrase “which words are relevant to other words in the sequence”; case B mentioned only “transformer.” Case C described attention and simultaneous token work. Case D also explained positional encodings preserving order.

## Limits discovered

- Four crafted examples are a smoke check, not an accuracy, false-coverage, missed-coverage, or latency benchmark.
- The model returns only a binary decision; the experiment does not yet capture evidence spans, ambiguity, user corrections, or confidence.
- The model call is synchronous and has a 30-second timeout; it has no retry, observability, streaming, or production failure policy.
- Token Factory availability, exact model versions, pricing, and structured-output behavior must be reconfirmed as work continues.

## Phase 1 comparison

The [small four-model benchmark](BENCHMARK.md) reuses these exact cases and validation. Across 48 live requests, Super passed 12/12, Nano 11/12, Ultra 6/12, and Lightning 0/12 under the unchanged 300-token cap. Super remains the provisional choice; all failures hit the token limit. See the report for timings, token counts, reproduction, and limitations.

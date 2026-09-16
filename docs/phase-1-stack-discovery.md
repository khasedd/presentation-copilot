# Phase 1 — Stack discovery record

## Scope and evidence

This record captures the project owner's Phase 1 test results and current semantic-coverage stack decision. The manual access, inference, and failure tests below were supplied by the owner; they were not rerun when this document was created. Their execution timestamps and full request configurations were not supplied. The semantic-coverage comparison is backed by the repository's [September 16, 2026 benchmark report](../experiments/BENCHMARK.md) and [per-request JSON results](../experiments/results/semantic-benchmark-2026-09-16.json).

No credentials or private reasoning content are stored here. Observed API behavior is distinguished from intended future application behavior.

## 1. Model availability and account access

Request: `GET /v1/models`, authenticated with the real `NEBIUS_API_KEY`.

The account could see these relevant NVIDIA model IDs:

- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
- `nvidia/Nemotron-3_5-Lightning`
- `nvidia/Nemotron-3-Ultra-550b-a55b`
- `nvidia/nemotron-3-super-120b-a12b`

**Conclusion:** Authentication worked and the intended Super model was available to the account. These observations establish access at test time, not a guarantee of future catalog availability.

## 2. Basic successful inference

Model: `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory's chat-completions endpoint.

Prompt:

```text
Reply with exactly: TOKEN_FACTORY_OK
```

Result: **HTTP 200**, with **3.520170 seconds total request time for this single request**.

Returned visible content, shown as a JSON string to preserve the leading newlines:

```json
"\n\nTOKEN_FACTORY_OK"
```

| Reported usage field | Tokens |
| --- | ---: |
| `prompt_tokens` | 26 |
| `completion_tokens` | 58 |
| `reasoning_tokens` | 49 |
| `total_tokens` | 84 |

The reported total is 26 prompt + 58 completion tokens = 84. The reasoning count is not an additional 49 tokens to add to that total.

**Conclusion:** A real Super chat-completions request succeeded. The owner observed visible content, reasoning content, usage accounting, and model metadata in the response structure. Plain-text responses can contain extra formatting or newlines even when exact wording is requested.

## 3. Semantic-coverage model comparison

Workload: the existing semantic-coverage POC's four cases—paraphrased coverage, keyword-only mention, partial coverage, and complete coverage. Each case was run three times per model: 12 attempts per model, 48 total. The cases, prompts, expected results, validation, temperature 0, JSON response mode, 300-token cap, and 30-second timeout were unchanged.

| Model | Correct, valid results | Mean latency per attempt | Aggregate output tokens (12 attempts) |
| --- | ---: | ---: | ---: |
| Nemotron Nano | 11/12 | 1.969 s | 3,245 |
| Nemotron 3.5 Lightning | 0/12 | 1.686 s | 3,600 |
| Nemotron 3 Super | **12/12** | **1.370 s** | **2,579** |
| Nemotron 3 Ultra | 6/12 | 0.810 s | 3,345 |

Super was the only model with perfect observed correctness in this fixed comparison and had the lowest aggregate output-token count; all other candidates exceeded 3,000. Token totals include failed attempts.

All 19 unsuccessful attempts hit the original 300-token cap (`finish_reason: length`) and failed coverage validation. There were no schema-valid semantic mismatches. These results measure usable correctness under the existing request settings, not general model intelligence. Four controlled cases repeated three times do not establish accuracy across realistic presentation speech.

### Keep the two latency measurements separate

| Measurement | Workload and sample | Meaning |
| --- | --- | --- |
| **3.520170 s** | One `TOKEN_FACTORY_OK` request | Total request time for a one-off basic inference check |
| **1.370 s** | 12 Super semantic-coverage attempts | Mean full-response request, parsing, and validation time in the benchmark |

These measurements come from different workloads and sample sizes. They must not be combined into one average or presented as interchangeable estimates. Neither is time to first token. The 2,579 output tokens belong to the semantic benchmark, while the 58 completion tokens belong to the one-off inference check.

## 4. Invalid model failure

Request used model ID: `nvidia/THIS-MODEL-DOES-NOT-EXIST`.

Result: **HTTP 404**.

```json
{"detail":"The model `nvidia/THIS-MODEL-DOES-NOT-EXIST` does not exist."}
```

**Conclusion:** The tested invalid model ID returned a clean 404 with a human-readable JSON error.

## 5. Malformed request failure

Request used the valid Super model ID but omitted the required `messages` field.

Result: **HTTP 422**.

```json
{"detail":[{"type":"missing","loc":["body","messages"],"msg":"Field required","input":{"model":"nvidia/nemotron-3-super-120b-a12b"}}]}
```

**Conclusion:** The tested schema-validation failure returned a structured HTTP 422 error identifying the missing field.

## 6. Client-side timeout behavior

Request: valid Super inference request with `curl --max-time 0.5`.

Observed curl error:

```text
curl: (28) Operation timed out after 500 milliseconds with 0 bytes received
```

Reported HTTP value: `000`.

**Conclusion:** The client timeout fired before a response arrived. Curl exited with code 28 and received no HTTP response. **`000` is curl's representation of no HTTP response, not a Nebius server status code.** This test does not establish whether server-side inference stopped or whether usage was charged after the client disconnected.

Expected future Presentation Copilot behavior on timeout:

- Do not mark new concepts as covered.
- Do not auto-advance.
- Preserve the last trusted state.
- Allow retry or degraded behavior.

These are intended application requirements, not implemented or verified state-management/advancement behavior. The current isolated POC does not contain those subsystems.

## 7. Authentication failure

Request: valid endpoint and model, with a deliberately fake Bearer token.

Result: **HTTP 401**.

```json
{"detail":"Couldn't authenticate. Reason: Unable authenticate"}
```

**Conclusion:** The tested invalid credentials produced a clear 401 authentication failure.

## 8. Current semantic-coverage stack decision

**Use Nebius Token Factory with `nvidia/nemotron-3-super-120b-a12b` for the current semantic-coverage workload.**

Rationale:

- Super achieved 12/12 correct, valid results in the existing benchmark; Nano achieved 11/12 and the other candidates scored lower.
- Its semantic-coverage mean latency was 1.370 seconds.
- Its aggregate completion-token usage was the lowest of the tested models: 2,579 across 12 attempts.
- Observed usable correctness takes priority over a modest token-cost difference. The owner accepts a potentially higher token price in exchange for that correctness. This is a decision preference, not a verified price comparison: current dollar rates, credit deductions, and total monetary cost were not established by these tests.

**Do not add extra Nebius deployment infrastructure solely for semantic coverage yet.** Token Factory already supplies the hosted inference path needed by the current workload. Nebius performs the actual inference hosting and NVIDIA Super performs the actual semantic judgments, so both are substantive parts of this path. No additional service or deployment dependency is selected by this record.

This is the current workload choice, subject to broader evaluation; it is not a production-readiness claim. Representative speech, ambiguity, corrections, false-coverage rates, concurrency/throughput, context limits, quotas, and pricing/credit consumption remain to be investigated. Additional Nebius infrastructure may be considered when another demonstrated requirement calls for it.

## Roadmap relationship

This record adds evidence for authenticated access, successful inference, observed API failure behavior, and the current component decision. It supplements the [Phase 1 roadmap](../roadmap.md) and existing benchmark rather than declaring all of Phase 1 complete. The exit gate's cost/credit evidence is still outstanding, and the future timeout behavior above requires later state and control work.

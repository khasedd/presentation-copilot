# Phase 1/2 workload trial — September 26, 2026

Status: completed live against the global Token Factory endpoint. **This trial does not close the separate provider-operations follow-ups.** It supports the provisional model choice and the extractive Phase 2 prototype. It is not a live transcription, guidance-product, safety or production-capacity test.

## Reproduce

```bash
python3 -m unittest discover -s tests -q
python3 -m experiments.foundation_probe --output presentation-output/new-foundation-trial.json --rounds 2
```

The runner reads the existing local `NEBIUS_API_KEY` configuration. It reserves a new owner-only output file before making requests, refuses overwrites, uses one worker and no retries, bounds request/response sizes, refuses redirects, and uses a 30-second socket timeout. Only synthetic repository-authored content is sent. The 54 requests used a 1,024-token completion budget, temperature zero and JSON-object output. The original 300-token benchmark remains unchanged.

Three small synthetic decks represent engineering controls, business rollout and an educational explanation. Each contains direct text, a nested group, meaningful presenter notes plus a procedural note, and repeated slide content. Extraction must select exactly the three authored statements with valid source references. Coverage uses about 1,000 words of earlier neutral speech followed by paraphrases covering two of three concepts. Reminder selection must return the sole uncovered statement verbatim. This last task is deliberately simpler than future adaptive guidance.

Quality expectations were encoded before the live requests. Extraction uses an exact-statement oracle, stricter than a general semantic oracle. Passing proves these specific outputs, not representative population accuracy. The trial has only two rounds and six observations per model/workload. Reported p95 is nearest-rank and equals the sample maximum; it is not a reliable tail estimate.

## Measurements

| Model | Workload | Correct | Mean seconds | Sample p95 seconds | Input tokens | Completion tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Nano | Extraction | 3/6 | 5.067 | 6.395 | 1,726 | 4,699 |
| Nano | Coverage | 5/6 | 3.016 | 4.796 | 7,394 | 2,545 |
| Nano | Reminder | 6/6 | 1.312 | 2.028 | 622 | 868 |
| Super | Extraction | 6/6 | 2.870 | 3.318 | 1,726 | 2,386 |
| Super | Coverage | 6/6 | 2.147 | 2.629 | 7,394 | 1,541 |
| Super | Reminder | 6/6 | 1.669 | 1.858 | 622 | 966 |
| Ultra | Extraction | 6/6 | 2.047 | 2.547 | 1,726 | 3,220 |
| Ultra | Coverage | 6/6 | 1.792 | 2.018 | 7,394 | 2,042 |
| Ultra | Reminder | 6/6 | 1.259 | 1.318 | 622 | 1,164 |

Nano included the procedural instruction in its engineering concept twice, truncated one extraction at the token cap, and missed the six-weeks/month-and-a-half paraphrase once. Source quotation alone did not reject the procedural note: presenter review is still mandatory. Super and Ultra each passed 18/18.

The inspected prices match the public input/output rates per million: Nano $0.06/$0.24, Super $0.30/$0.90, Ultra $1/$3 (taxes excluded). Multiplying reported usage, including failed attempts, gives **estimates** of $0.0025314, $0.0073263 and $0.029020 respectively: **$0.0388777 total**. This is not a settled bill or measured grant debit. Reasoning, where generated, is already included in completion usage; it is not counted twice.

Observed mixed-workload serial service rates, `60 × attempts / sum(request seconds)`, are 19.16, 26.92 and 35.31 requests/minute for Nano, Super and Ultra. These are measurements of this short sequential trial, not sustainable account capacity. A five-second coverage cadence is a reasonable next experiment; a one-second cadence is unsupported by these measurements.

Prompt usage ranged from 100 to 1,237 tokens. The `/models` catalog exposes no context/output ceilings. Separate synthetic Super probes established a **262,144-token combined reservation boundary** for the tested prompt: usage reported 20 prompt tokens; `max_tokens=262123` and `262124` succeeded, while `262125` returned HTTP 400 naming 262,144 as the limit and 262,145 as the requested total. This checks prompt-plus-output reservation validation. It does not prove full-context quality or successful generation of 262,124 completion tokens; successful responses deliberately stopped after 23–50 tokens.

An earlier `max_tokens=262144` error reported a different prompt count (103), while all five successful probes reported 20 prompt tokens. Preserve that discrepancy rather than use error counts as a tokenizer. The prototype retains its much smaller character/request bounds. The exact served maximum with a different prompt/template and model-specific output ceilings remain provider-contract follow-ups. [All eight probe observations](results/context-boundaries-2026-09-26.json) retain HTTP status, numeric limits and usage, not error bodies or credentials. Payload: model `nvidia/nemotron-3-super-120b-a12b`, messages `[{"role":"user","content":"Return only {}."}]`, temperature `0`, and the recorded `max_tokens` value; global chat-completions endpoint, 30-second socket timeout, redirects refused.

All 18 Nano responses exposed rate-limit headers whose limits matched the inspected console defaults. All Super and Ultra responses omitted those headers; their limits were inspected in the console without API-header confirmation. Account-specific header values are redacted in the public results; header names and presence/absence are preserved. This contradicts the documentation's statement that limits are always visible in headers and must not be hidden by inventing headroom. No 429, timeout or refusal occurred live; mocked tests cover failures separately.

## Decision and remaining work

Retain Super for the current extraction/coverage prototype: both it and Ultra passed these cases, but Super's estimated total cost was about a quarter of Ultra's. Ultra was faster in this trial and remains a viable candidate if later deadlines justify the extra cost. Nano is unsuitable for automatic concept extraction under this contract. Prefer simple deterministic selection for the reminder task until Phase 6 establishes a need for generative guidance; passing a copy task does not validate adaptive advice.

Remaining account/provider follow-up includes quota aggregation/reservation semantics, the prompt-accounting discrepancy, independent maximum-output/full-context behavior and grant expiry/eligibility. Larger and adversarial semantic acceptance belongs to the already-listed Phase 4 tasks. Account-credit unknowns do not reopen the completed Phase 1 foundation. Phase 3 is the next active phase.

Allowlisted synthetic results with account-specific rate-limit header values redacted: [foundation-trial-2026-09-26.json](results/foundation-trial-2026-09-26.json). No credentials, raw reasoning, private slides, account identifiers or error bodies are included.

## Scheduled load and observed billing

Ran `python3 -m experiments.foundation_load --output presentation-output/foundation-load-2026-09-26.json`. The predeclared trial uses one worker for 36 coverage updates every five seconds, six competing reminder calls and three extraction calls. Each coverage result must be correct and arrive within five seconds of its scheduled time, including queue delay. This is a three-minute prototype trial, not a full presentation soak or a concurrency guarantee.

All **45/45 outputs were correct**, but only **35/36 coverage deadlines passed**, so the trial exited **1 (failed)**. Duration: 177.408 seconds. Coverage end-to-end mean: 2.418 seconds; nearest-rank p95: 4.473 seconds; maximum: 5.814 seconds. Update 26 queued for 1.923 seconds, then took 3.890 seconds in the request. The largest extraction response including competing work took 6.922 seconds. No HTTP/provider failure occurred. [Raw load results](results/foundation-load-2026-09-26.json) preserve the failed deadline.

The decision is **not to claim reliable five-second updates with competing extraction on one worker**. Extract concepts before a live session, and separately evaluate scheduling/cadence before integration. A passing average does not erase the missed deadline. This completed measurement identifies a constraint; it does not implement a Phase 5 scheduler or change acceptance targets after the run.

The load consumed 45,843 input and 11,431 completion tokens, an estimated $0.0240408. Combined with the 54-request comparison, the estimate is $0.0629185 before the tiny boundary probes.

After those two trials, actual posted usage/billing was observed in the authenticated Usage page and remained minimal. Provisioned credits were sufficient for the experiments performed. Posted Nano/Ultra token usage reconciled exactly to the original benchmark plus this comparison. Super's account activity included earlier usage beyond the committed comparison, so the full account total is not attributed solely to this task. These are observed billing results, not a claim that a month-end invoice has settled. The page's update timestamp was stale relative to the new totals; billing timing is not assumed instantaneous. Account totals and trial-credit balances are omitted; reproducible per-experiment token usage and cost estimates remain above and in the linked results.

# Phase 1 — Token Factory operating constraints

Reviewed **September 17, 2026** against official Nebius documentation and the public Token Factory model/endpoint UI. This is the project's dated reference for inference limits, costs, and operational dependencies. Recheck it before changing models, sizing live workloads, deploying, and demonstrating the project.

**Decision:** retain Token Factory + NVIDIA Super for isolated coverage experiments. The documentation review is complete, and the initial Phase 1 stack-discovery gate is closed by the repository's account-visible billing evidence; account capacity, exact credit reconciliation, and live reliability are not verified. No finite documentation review can establish zero future bottlenecks. The acceptance checks below make those risks explicit before integration depends on them.

Evidence labels used here: **documented** means a provider statement; **observed** means existing repository measurements or public UI inspected on the review date; **estimate** means arithmetic using those inputs; **required check** means unfinished work. No additional billable inference, billing changes, load tests, or infrastructure deployments were performed for this documentation review. The pricing page required login in the available browser; public model cards were readable. No private account values are recorded.

## 1. Quotas and rate limits

Documented in [Rate Limits & Scaling](https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits):

- Limits vary dynamically; get the base allocation from the account's Rate Limits page. **60 RPM / 400,000 TPM is an illustration, not our allocation.**
- Over rolling 15-minute windows, utilization of at least 80% raises the following limit by 20%; utilization at most 50% lowers it by division by 1.5. Growth stops at 20 times the base allocation; further capacity requires Enterprise.
- Exceeding a limit can return HTTP 429. Spare capacity sometimes permits lower-priority processing, signaled by `x-ratelimit-over-limit: yes`; this is not dependable headroom.
- Read `x-ratelimit-limit-{requests,tokens}`, `x-ratelimit-remaining-{requests,tokens}`, and `x-ratelimit-reset-{requests,tokens}`. Reset values and `Retry-After` are seconds; token headroom replenishes continuously.
- Additional headers: `x-ratelimit-dynamic-scale-{requests,tokens}`, `x-ratelimit-dynamic-period-remaining`, and `x-ratelimit-dynamic-period-usage-{requests,tokens}` expose scaling and utilization.
- The page mentions higher Batch API limits but does not specify its usable contract or numeric allocation.

**Required checks:** actual RPM/TPM; whether quotas aggregate by user, key, project, organization, model, or endpoint; input/output token accounting and any output reservation; concurrent-request and burst caps; availability of headers on success/error/streaming responses. None was established by the sequential benchmark. Extra keys must not be treated as extra capacity.

**Project design implications:** use one shared request budget for coverage, guidance, extraction, retries, and experiments. Keep live coverage ahead of background work. Coalesce transcript changes; do not send a request for every partial transcription event. Bound concurrency and queue length, expire stale jobs, and honor retry delays with bounded jittered backoff only while the result remains useful. Do not generate waste traffic to induce quota growth. These are future requirements, not implemented behavior.

## 2. Prices and hosted context windows

**Observed public UI**, Base / Global endpoints. USD per **1,000,000** tokens, input and output charged separately. The UI labels prices approximate and links to the authenticated [organization pricing page](https://tokenfactory.nebius.com/organization/prices); account-specific discounts and invoices were not inspected. Context notation below is preserved exactly as displayed, not converted into an assumed exact integer limit.

| Exact API routing key | Input / 1M | Output / 1M | Hosted context display | Quantization | Official model card |
| --- | ---: | ---: | --- | --- | --- |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | $0.06 | $0.24 | 262K | FP8 | [Nano](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNVIDIA-Nemotron-3-Nano-30B-A3B) |
| `nvidia/Nemotron-3_5-Lightning` | $0.06 | $0.24 | 1,024K | BF16 | [Lightning](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNemotron-3_5-Lightning) |
| `nvidia/nemotron-3-super-120b-a12b` | $0.30 | $0.90 | 256K | FP4 | [Super](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2Fnemotron-3-super-120b-a12b) |
| `nvidia/Nemotron-3-Ultra-550b-a55b` | $1.00 | $3.00 | 1,024K | FP4 | [Ultra](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNemotron-3-Ultra-550b-a55b) |

All four detail cards show text-to-text, tool calling and reasoning available, public endpoints available, and dedicated endpoints, full/LoRA fine-tuning, and custom speculators unavailable. This is platform availability on the review date, not a prediction about sales-arranged deployments. Super's endpoint dialog also advertises Responses API support; that path has not been tested here. Catalog-wide availability labels alone are insufficient: inspect the detail card and authenticated routing key.

The cards display throughput figures, but they do not establish our complete-response latency, quota, or concurrent-user capacity. Super's displayed 127 tokens/s must not replace the repository's measured 1.370-second mean and 3.120-second maximum across 12 tiny requests. Some catalog parameter counts display `0B`, so model metadata should be checked before use rather than accepted indiscriminately.

**Context policy for future experiments:** budget system instructions, slide concepts, transcript, serialization/chat-template overhead, optional tools/images, and reserved completion together. Count using the selected model's tokenizer; reconcile against returned usage. Obtain the exact served token ceiling and maximum completion size, then test below/at/above it with synthetic content. Model-family advertised context is not proof of a hosted endpoint's limit. Use a bounded transcript window and explicit summaries; a full growing transcript resent every update can make total input consumption grow quadratically with presentation duration.

## 3. Credit usage and billing

Documented in [Billing & Consumption](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new): onboarding requires a billing account and bank card; the standard first-signup grant is **$1, valid 30 days**. This is distinct from any hackathon award.

Usage debits the balance in real time. Card billing occurs when the configured threshold is reached or at month start for a negative balance, bringing it back to zero. A failed charge suspends the account. Manual top-ups are available; a credit balance is **not a verified hard spending cap**. Company accounts can arrange bank transfers.

Promo codes have redemption expiry conditions and cannot settle outstanding invoices. Confirm applied credit in Transactions. Review organization Usage with project/service/product/region filters for reconciliation. Taxes depend on billing location; the table's estimates exclude them.

**Observed account billing evidence:** the settled [Token Factory Usage dashboard screenshot](evidence/phase-1/nebius-token-factory-billing.png) shows **$0.02 total** for the recorded activity. It lists input and output usage for Nemotron Ultra, Lightning, Nano, and Super in `eu-north1`; Super input and output are each displayed as `< 0.01M` tokens and `< $0.01`. This is actual observed dashboard billing evidence, not a retrospective estimate. The screenshot does not expose the exact underlying quantities, account balance, or credit-consumption order.

**Remaining account follow-up:** remaining promotional and paid balances, grant expiry after redemption, eligible services/models, charging threshold, tax treatment, credit-consumption order, and whether any enforceable spending ceiling exists. Never assume Token Factory credits cover AI Cloud GPUs or dedicated endpoints. These items do not block the Phase 1 exit gate; they remain relevant before budgeting or production use.

The [official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules) offer Builder Program credits but do not establish our award amount or expiry. They require runtime Nebius use plus an NVIDIA open-source model; separate Cloud hosting is not mandatory for the current track. Test access must remain available through judging, currently ending **December 15, 2026, 12:00 PM Pacific**. Budget beyond the October submission deadline. No new provider or model is selected by this review.

### Cost calculation and existing evidence

For ordinary uncached text usage at the table's rates:

```text
request USD = (prompt_tokens × input_USD_per_1M
             + completion_tokens × output_USD_per_1M) / 1,000,000
```

Nebius's [official OpenCode cookbook](https://dev.nebius.com/cookbook/opencode-nebius-token-factory) explains that reasoning tokens are already included within output usage and billed at the output rate. Count them once. Do not estimate cost from visible JSON length. No cache discount, Batch discount, or service-tier discount is assumed: applicable rate, eligibility, and reported cached-token semantics need verification.

Using recorded [benchmark usage](../experiments/BENCHMARK.md), including unsuccessful attempts, with today's public prices gives the following **retrospective estimates, not measured bills or historical price claims**:

| Model | Input tokens | Completion tokens | Estimated USD for 12 attempts | Usable results |
| --- | ---: | ---: | ---: | ---: |
| Nano | 3,069 | 3,245 | $0.00096294 | 11 |
| Lightning | 3,069 | 3,600 | $0.00104814 | 0 |
| Super | 3,069 | 2,579 | $0.0032418 | 12 |
| Ultra | 3,069 | 3,345 | $0.013104 | 6 |

Super averaged 255.75 input and 214.9167 completion tokens, approximately **$0.00027015 per attempt**. The owner's separate 26-input/58-completion smoke request would cost approximately **$0.00006** at these prices. These are retrospective per-request estimates and do not replace the settled dashboard total; the screenshot does not reconcile the total to individual requests. Truncated but processed generations still belong in the usage estimate; timeout/disconnect and error billing remain unresolved.

### Sizing examples — estimates, not accepted cadence or capacity

One coverage request per update, one presenter, 60-minute session, Super pricing, no retries or guidance:

| Update interval | RPM | Requests/hour | Hour at tiny benchmark mean | Hour at 2,000 input + 300 output/request |
| --- | ---: | ---: | ---: | ---: |
| 1 second | 60 | 3,600 | $0.97254 | $3.132 |
| 2 seconds | 30 | 1,800 | $0.48627 | $1.566 |
| 5 seconds | 12 | 720 | $0.194508 | $0.6264 |

The larger example at 2-second cadence consumes 69,000 total generated/input tokens per minute arithmetically; provider TPM accounting still needs confirmation. Ten such presenters need 300 RPM and 690,000 tokens/minute before guidance, setup, retries, or reserve. A 60-RPM allocation would be exhausted by one presenter at 1-second cadence even if token headroom remained. These calculations demonstrate why both quotas matter.

For workload classes `w`, compute `RPM = sum(sessions_w × 60 / interval_seconds_w)` and estimated `TPM = sum(RPM_w × (input_w + output_w))`, adding setup/background traffic separately. At the measured 1.370-second mean, a serialized worker cannot sustain one request each second. Parallel requests would require stale-result protection and a measured concurrency budget. Size against tail latency and bursts, not that mean.

## 4. API contract and compatibility traps

[Quickstart](https://docs.tokenfactory.nebius.com/quickstart) documents `https://api.tokenfactory.nebius.com/v1/`, Bearer API-key authentication, and `POST /chat/completions`. Keep keys server-side in environment configuration. Existing authenticated `/v1/models` and inference evidence remains in the [stack discovery record](phase-1-stack-discovery.md); it was not rerun here. Model names and casing must match routing keys, not display names.

Key [chat-completion reference](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion) constraints:

| Field | Documented constraint |
| --- | --- |
| `model`, `messages` | Required; at least one message |
| `max_tokens` | Nonnegative; defaults to 8,192 if absent/null; prompt plus reservation must fit context |
| `max_completion_tokens` | Nonnegative; includes visible and reasoning tokens |
| `temperature`, `top_p` | 0–2 and 0–1 respectively |
| `n` | 1–128; default 1; extra completions consume quota |
| `stop` | At most four sequences |
| `stream` | SSE deltas ending with `[DONE]` |
| `stream_options.include_usage` | Final chunk carries usage when enabled |
| `service_tier` | `auto`, `default`, `over-limit`, `flex`, `no-limit`; default `auto` |
| `ai_project_id` | Optional project query parameter |

The reference exposes `reasoning_effort`, but per-model support needs testing. Tier names do not establish entitlement, priority, pricing, or unlimited capacity. Do not send both token-limit fields until their precedence is verified. A disconnected stream may lose final usage. `store` describes output storage for distillation; it is not proof of organization-wide ZDR.

[Structured-output guidance](https://docs.tokenfactory.nebius.com/ai-models-inference/json) documents both `json_object` and `json_schema` with model-dependent support. **Documentation conflict:** the chat reference's `response_format` description lists only text/JSON-object. Keep the proven JSON-object contract until Super's exact schema dialect and failure handling have been tested. JSON syntax/schema adherence never proves semantic coverage; retain local checks for concept IDs, allowed statuses, and consistency. Reject refusals, missing content, malformed/truncated output, and incomplete streams.

The existing benchmark's 19 failures reached the **client-selected 300-token completion cap**. This is not Nebius's context limit. Test a larger bounded budget and supported reasoning controls separately, preserving the original benchmark for comparison. Never interpret an interrupted reasoning-only response as coverage.

[Inference overview](https://docs.tokenfactory.nebius.com/ai-models-inference/overview) describes Base/Fast configurations and vLLM parameters. A `-fast` name is usable only when the catalog actually exposes that endpoint. SDK-level `extra_body` and raw HTTP payload shape must be validated for the chosen client. OpenAI compatibility is not a promise that every OpenAI endpoint, parameter, or model-specific option works.

### Adjacent workloads across the roadmap

| Workload | Constraint and next evidence |
| --- | --- |
| Slide extraction | Text can use the current path after evaluation. Diagram/image understanding needs a vision model; Super's card is text-only. [Vision examples](https://docs.tokenfactory.nebius.com/api-reference/examples/vision-capabilities) allow image URLs or base64. Verify supported formats, bytes, resolution, image count, token accounting, and URL access/privacy before selecting the adapter. No universal payload/image cap was established. |
| Transcription | No audio transcription or realtime microphone endpoint was identified in the reviewed [documentation index](https://docs.tokenfactory.nebius.com/llms.txt). SSE text generation is not speech recognition. Phase 3 must select and validate ASR independently. Absence from this review is not a claim that Nebius can never host ASR. |
| Embeddings/retrieval | [Embedding API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-embeddings) accepts text/token inputs and arrays, float/base64 output, and a dimensions parameter. Verify actual model dimensions, per-input context, aggregate batch/input limits, truncation behavior, pricing, and access before adoption. Do not import another provider's limits. |
| Offline extraction/evaluation | Batch is a possible investigation, not a selected dependency. Endpoint support, job/file limits, queue deadlines, cancellation, retention, pricing, and credits are unverified. Keep offline work out of the live request budget. |
| Guidance | Separate budget and shorter response contract; suppress obsolete guidance. An extra guidance call per coverage update can approximately double RPM even if it uses few tokens. |
| Automatic advancement | No provider tool-call capability authorizes slide movement. Only validated, current judgments may feed a separately tested conservative state/control layer. |

## 5. Availability, deployment, and privacy

[Public Serverless Endpoints](https://docs.tokenfactory.nebius.com/public-serverless) documents shared infrastructure, Global routing, and processing locations that can change without notice. Region-specific base URLs may stop working after relocation. Public endpoints are intended for testing/non-critical use where that variability is acceptable; a stable processing region requires a dedicated endpoint. Keep the documented global base URL for the existing experiment. Real presenter-network latency and failure behavior still require measurement.

[Dedicated capacity guarantees](https://docs.tokenfactory.nebius.com/ai-models-inference/dedicated-endpoints/capacity-and-scaling) state that self-service capacity is on-demand: minimum replicas are held only while active. Stops, incidents, and maintenance release capacity; restart can wait for GPUs. Scaling above minimum depends on availability. **There is no formal self-service SLA without a contract**; historical ~99.9% success is not an SLA. Reserved capacity requires a sales arrangement. The four chosen NVIDIA cards currently do not offer self-service dedicated deployment, so this is not an immediately verified fallback.

[Dedicated billing](https://docs.tokenfactory.nebius.com/ai-models-inference/dedicated-endpoints/billing-policy) ties charges to running replicas and PAYG scaling. It lists ready capacity as billable and provisioning/not-ready/partially-ready, replica restarts, and graceful shutdown as not billed. The general running-replica rule and partially-ready exception need clarification before cost planning. Rates and contracts must be checked separately; do not apply public per-token prices to dedicated compute or assume idle running capacity is free.

[Legal Quick Guide](https://docs.tokenfactory.nebius.com/legal/legal-quick-guide) says default inputs/outputs may be retained for speculative decoding. Organization-wide ZDR covers projects/endpoints and prevents retention beyond in-flight processing; enabling it may affect speed. Its FAQ says content is not used for model training in either mode. The guide is subordinate to the applicable agreement, DPA, and privacy policy. Obtain confirmation of effective ZDR and the relationship to request-level `store` before sending sensitive presentation content. Avoid retaining raw transcripts or private reasoning in operational logs.

**Time-sensitive observed notice:** on September 17 the [public console](https://tokenfactory.nebius.com/models/catalog) announced a primary storage move from Finland to France starting **September 21, 2026**, with a temporary CPL/operations read-only period. The legal guide still describes Finland storage. Confirm the migration schedule, affected operations, and current location before setup/demo or privacy commitments; this notice does not establish an inference outage or a globally pinned processing region.

[Organizations and Projects](https://docs.tokenfactory.nebius.com/team-access/org-projects) describes project-isolated resources inheriting access settings. Verify the intended project for experiments and deployment; successful authentication alone does not establish resource permissions or billing attribution.

## 6. Monitoring, failures, and model lifecycle

[Inference Observability](https://docs.tokenfactory.nebius.com/ai-models-inference/observability) explicitly limits metrics access to dedicated inference despite introductory references to public endpoints. Do not assume the public experiment has those dashboards. Documented metrics include throughput, latency percentiles, errors, and cache hits; TTFT is streaming-only. Dashboards are not billing reconciliation. Use organization Usage for billing and client telemetry for the public path. The [Nebius status page](https://status.nebius.com/) is the linked incident-history source, not proof of our app's health.

Future telemetry should record timestamp, model/routing key, request/session revision identifier, latency, finish reason, token counts, retry count, error class, and rate-limit headers. Log no credentials or raw private content. Track usable-result latency separately from HTTP success; a fast invalid response is not a successful coverage update. Record missing usage as unknown.

| Failure | Evidence and required application behavior |
| --- | --- |
| 401 | Owner's invalid-key test; stop retrying blindly and repair authentication. |
| 404 | Owner's invalid-model test; recheck catalog/access/retirement, not an automatic model substitution. |
| 422 | Owner's missing-messages test; fix request validation. |
| 429 / over-limit | Documented quota pressure; bounded backoff, lower cadence, shed background work. |
| Network timeout / 5xx | Timeout observed locally; transient-server handling is a future test. Enforce a useful-result deadline; retries may incur additional cost. |
| `finish_reason: length`, invalid JSON, refusal | Reject result; investigate output/reasoning budget or contract. |
| Stale/out-of-order valid result | Ignore if session, slide, source, or transcript revision no longer matches. |
| Billing suspension / provider outage | Preserve trusted state, show unavailable/degraded status, keep manual presentation control. |

These handlers are design requirements, not implemented by this documentation. Never advance on failure or uncertainty. The prior curl `000` was absence of an HTTP response, not a server status. Neither the existing timeout test nor the reviewed docs establishes cancellation, refund, idempotency, or billing after disconnection.

[August 2026 deprecation notice](https://docs.tokenfactory.nebius.com/august-2026-deprecation-notice) removed affected serverless IDs August 31 and explicitly disclaims automatic rerouting. It recommends Super for the old `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1`; that old Ultra is different from our tested Nemotron 3 Ultra. Some retired names still appear in catalog listings/examples. Check authenticated availability and a successful request before any dependency change, and re-run quality/latency/cost evaluation before switching models.

## 7. Phase 1 closure checklist

These are evidence requirements, not extra infrastructure commitments. The project owner supplies account-only facts; the next engineering experiment records technical measurements. Never paste API keys, card information, invoice identifiers, or promo codes into Git.

| Open item | Evidence needed to close | Blocks |
| --- | --- | --- |
| Account capacity | Sanitized Rate Limits values plus successful-request headers; quota scope, token accounting, burst/concurrency semantics confirmed | Supported presenter count/cadence |
| Credits and effective billing | Sanitized amount/expiry/eligible-service facts, actual rates, threshold/cap policy; isolated synthetic usage reconciled with Usage/Transactions after settlement. The settled dashboard already records $0.02 for the observed activity. | Credit runway and spending policy before budgeting or production use |
| Model context/output | Exact endpoint ceilings, tokenization, below/at/over-boundary results, truncation behavior, reasoning/schema compatibility | Safe prompt sizes and extraction workloads |
| Live workload envelope | Agreed maximum presenters, session length, cadence, p95/p99 usable-result deadline, error tolerance, and spend budget; realistic replay with retries and competing jobs | Any no-bottleneck readiness claim |
| Realistic capacity trial | Cold/idle start, sustained expected load, bounded bursts and soak; latency percentiles, quota headroom, valid results, costs, and recovery | Integrated live sessions |
| Failure contract | Controlled timeout, throttling simulation, malformed response, interrupted stream, stale result; account suspension handled without deliberately causing it | Safe state integration and later advancement |
| Privacy and migration | Effective ZDR, retention/processing location, `store` semantics, September 21 operation impact verified | Sensitive content and deployment assumptions |
| Missing provider contracts | Support answers for request bytes, server timeouts, cancellation/idempotency/error billing, relevant Batch/cache/tier rules | Any design relying on those capabilities |
| Availability fallback | Account access/deprecation preflight; measured recovery; if requirements exceed public service, confirmed Super hosting/capacity offer and price | Production reliability commitments |

For a first sizing experiment, reserve **30% quota headroom** as a project planning assumption, then revise from measured bursts. Define acceptance targets before the trial; the current benchmark does not supply production targets. If public inference cannot meet them, resolve cadence/workload size or confirmed hosting capacity before integration. No untested model fallback may silently change coverage judgments.

**Verification of this record:** official pages and four public model detail cards were read, prices/context/routing keys compared, cost arithmetic recomputed from the committed benchmark totals, repository cross-links checked, and the settled Usage dashboard screenshot inspected. The $0.02 total is recorded as actual observed billing evidence. Documentation contradictions and account-only unknowns are deliberately retained. The Phase 1 stack-discovery exit gate is complete; the checklist above remains follow-up evidence for integrated live sessions, budgeting, privacy commitments, and production-readiness claims.

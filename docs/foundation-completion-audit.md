# Foundation completion audit — September 26, 2026

The owner required completion of Phases 0–2 before further Phase 3 work; that foundation gate is now complete. Existing verified work remains historical evidence; nothing is silently deleted, deferred or declared production-ready. Phase 3 is the next active phase.

## Phase 0: dated compliance review

Re-read the official [rules](https://nebiusglobalaihackathon.devpost.com/rules), [overview](https://nebiusglobalaihackathon.devpost.com/) and [resources](https://nebiusglobalaihackathon.devpost.com/resources) on September 26. The engineering constraint remains substantive runtime Nebius inference/cloud plus an NVIDIA open model. Best Apps and Agents remains the selected track. Authorized Google Slides ingestion does not replace that AI path.

The submission deadline remains October 30, 2026 at 10:00 AM Pacific. Provide a public open-source repository, reproducible instructions, working judge access through December 15 at noon Pacific, an English description, a public demonstration video no longer than three minutes, and provider feedback. These are future submission deliverables, not claims that submission is complete. Confirm ownership/licenses for included assets and disclose significant in-period changes if applicable. The recurring rules review is now a standing rule plus the existing final submission check, with this dated review completing the foundation task.

The resources page advertises Token Factory credit opportunities. Hackathon/provider credits were successfully provisioned and were sufficient for the experiments performed. Advertised offers are not proof of grant expiry or service eligibility. No application, redemption, registration or legal acceptance was performed during this review.

## Phase 1: infrastructure investigation

This is research, not a deployment or an assumption that credits cover compute.

| Option | Appropriate workload | Current decision and reason |
| --- | --- | --- |
| Token Factory public inference | Hosted NVIDIA text-model calls | Retain for extraction and semantic experiments; already authenticated and measured. Shared capacity and routing remain limitations. |
| Serverless Jobs | Finite containerized preprocessing, evaluation or ASR batch trials | Investigated; do not deploy for the current small Python experiment. A batch job is not a live stream service. |
| Serverless Endpoints | Custom inference in a container behind HTTP | Candidate if hosted ASR/vision is needed; requires separate runtime, capacity, privacy, license and cost validation. Not selected. |
| DevPods / current Devlabs | Interactive exploration and debugging | The March announcement used DevPods; the current product page calls this option Devlabs. Not an application deployment target for this milestone. |
| AI Cloud VMs / managed clusters | Explicit control over model runtime and GPU resources | Available alternatives, but no demonstrated need justifies provisioning or paying for persistent GPUs now. |

Sources: [current serverless services](https://nebius.com/serverless), [original DevPods announcement](https://nebius.com/blog/posts/introducing-serverless), [Jobs documentation](https://docs.nebius.com/serverless/jobs/manage), [Endpoints documentation](https://docs.nebius.com/serverless/endpoints/manage), and [Nebius's runnable serverless examples](https://github.com/nebius/serverless-ai-cookbook). Current documentation takes precedence over launch-era preview promises; account/region availability is not proven by a product page. The hackathon requires Nebius runtime use, not purchase of every Nebius service.

## Workload assignment and model candidates

| Workload | Component and rationale | Evidence boundary |
| --- | --- | --- |
| Presentation ingestion | Google Slides REST + deterministic Python normalization | Preserves direct content and provenance without an LLM; existing live source verification remains valid. |
| Concept extraction | NVIDIA Super via Token Factory, followed by exact-source validation and presenter review | New extractive prototype; outputs are drafts, not automatically approved requirements. Nano and Ultra evaluated with the same contract. |
| Semantic coverage | NVIDIA Super via Token Factory + local contract validation | Existing four-case benchmark and the new longer-context trial; broader Phase 4 acceptance is still separate. |
| Guidance | Prefer deterministic selection from reviewed uncovered concepts initially; compare model reminder selection during stack discovery | The trial investigates model suitability only. No Phase 6 product, timing policy or UI is implemented. |
| Transcription | A speech-specific component, separate from these three text models | Phase 3 selection remains open. None of the compared endpoints is asserted to accept microphone audio. |
| Embeddings | No component selected | A current slide's small concept set can be sent directly; retrieval is not a demonstrated requirement. |
| Images/charts | Explicit unsupported markers and presenter review | No vision model, OCR, external image fetch or chart interpretation selected. |

NVIDIA describes the [Nano/Super/Ultra family](https://research.nvidia.com/labs/nemotron/Nemotron-3/) as open models with differing efficiency/reasoning trade-offs. [Super's release](https://blogs.nvidia.com/blog/nemotron-3-super-agentic-ai/) identifies open weights under a permissive license; the [Ultra card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16) identifies OpenMDW 1.1. A hosted routing key and a downloadable weight variant are distinct artifacts: no weights, training data, SDK or new inference provider are added by this change. Before self-hosting, inspect the exact chosen variant's license and notices; family branding is not a blanket license for every model or dataset.

The substantive path is direct: source-backed statements → Token Factory → NVIDIA model judgment → local validation. Removing Nebius/NVIDIA removes the actual semantic inference, not a decorative integration. The current choice remains provisional because discovery results cannot establish safe advancement or full live-session reliability.

## Account evidence inspected read-only

After the owner signed in, Token Factory rate limits were inspected read-only and were adequate for the current experimental workload. This does not establish production capacity or guarantee response deadlines.

Billing was active, and actual usage/billing was observed and remained minimal during the experiments. Provisioned hackathon/provider credits were sufficient for the experiments performed. These observations do not establish that a month-end invoice has settled. Account balances, trial balances/duration and credit transactions are omitted from this public record.

The UI locates quotas under a project and lists individual models; the [public rate-limit documentation](https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits) still describes a user allocation. The complete aggregation scope, output reservation and burst semantics require confirmation; do not multiply capacity by creating keys. The trial's returned header names are recorded separately; account-specific values are redacted.

**Credit-terms follow-up:** expiry and service restrictions remain unverified. These account-operations follow-ups do not reopen or invalidate the already-passed Phase 1 exit gate.

**Non-blocking provider-operations follow-up:** authoritative expiry and eligible-service terms for the provisioned grants; quota aggregation/reservation semantics; reconciliation of provider prompt accounting with returned usage; model-specific maximum-output/full-context behavior. The [workload report](../experiments/FOUNDATION-TRIAL.md) includes 99 comparison/load calls, reservation-boundary probes, actual posted usage and a failed five-second deadline. Longer sessions and production concurrency remain unproven, not a hidden readiness claim. Console access resolves some account facts, not undocumented provider contracts. These questions remain explicitly unverified operational evidence; they do not invalidate the completed Phase 1 foundation or block Phase 3. See the [non-blocking provider-operations checklist](phase-1-token-factory-constraints.md#7-non-blocking-provider-operations-checklist).

## Phase 2: source formats and edge cases

The source-format investigation already existed in the [Phase 2 decision](phase-2-presentation-representation.md#source-decision-and-suitability): Google Slides is selected, PPTX is a future adapter candidate, and PDF is deferred. Investigation does not require implementing every format. The previously unchecked investigation item is reconciled to that evidence; no new source dependency is introduced.

| Case | Verified handling | Explicit limit |
| --- | --- | --- |
| Sparse/blank slide | Preserve order and content; draft status distinguishes no supported text | Empty drafts never mean complete coverage. |
| Diagram/image/chart | Preserve source IDs and available alt metadata; unsupported markers survive | No rendered or chart meaning inferred. Alt text is not visual understanding. |
| Repeated concepts | Identical quotes on one slide are rejected as duplicate model output; repetition on separate slides remains separate | No deck-wide semantic deduplication or persistent identity claim. |
| Reorder | Existing live comparison evidence plus new nested-source reference test | Drafts belong to one snapshot; re-extract/rebind after changes. |
| Presenter notes | Only designated notes shape contributes evidence | Procedural notes are excluded by the prompt and inspected during evaluation, not guaranteed by quote matching alone. |
| Nested groups | New group-inside-group synthetic cases preserve exact child references | Live fixture still demonstrates only one group level. |
| Tables | Existing merged-cell tests and new coordinate-addressed extraction units | No invented row/header relationships; presenter review is needed. |
| Malicious/malformed output | Reject unknown references, invented quotes, duplicate fields/concepts and invalid shapes; provider failures remain explicit | Exact quotation proves source support, not semantic importance or immunity to prompt injection. |

The extraction sidecar uses `concept-drafts/1.0`, the exact source snapshot ID, slide fingerprint, local concept IDs, and support references (including table cell coordinates). It does not alter ingestion schema 1.0 or the comparator, invent confidence, carry coverage, or activate controls. Its 16,000-character source limit is a local guard, not a provider token ceiling. Oversized input is rejected rather than silently truncated.

# Presentation Copilot roadmap

`roadmap.md` is the authoritative engineering roadmap and verified historical record for Presentation Copilot. External planning/task systems, including Career OS, may derive tasks from it but must not introduce a competing technical sequence. Checked items describe completed, verified work only; unchecked items remain planned work or investigation. The official [Devpost rules](https://nebiusglobalaihackathon.devpost.com/rules) remain the controlling compliance source.

**Current priority: Phase 3 — speech capture and transcription.** Phases 0–2 are complete for the project foundation. Remaining account/provider questions are non-blocking provider-operations follow-ups; they do not reopen the completed Phase 1 foundation or block Phase 3. Preserve the existing Phase 3 transcript slice and Phase 4 proof of concept as bounded historical work while Phase 3 continues. Any proposed scope change must be explicit and approved by the owner.

**Standing compliance rule:** recheck official rules, overview, resources and submission requirements before each major compliance decision and again before submission. Each review is a dated event; future reviews are an ongoing obligation, not an eternally incomplete Phase 0 deliverable.

## Phase 0 — Project definition and hackathon foundation

- [x] Explored multiple possible Project 1 ideas and selected/locked Presentation Copilot as Project 1.
- [x] Defined the speech-aware presentation-tracking concept: semantic slide coverage, a live covered/uncovered checklist, adaptive AI-assisted speaker notes, and eventual conservative automatic advancement.
- [x] Considered overall feasibility, distinguished resume/demo scope from a future production-quality system, and considered infrastructure cost.
- [x] Selected the Nebius x NVIDIA Global AI Hackathon as the foundational project context, targeted the Best Apps and Agents Track, and made substantive Nebius plus NVIDIA open-source AI use a permanent constraint.
- [x] Established the initial repository documentation, secret-handling guidance, MIT license, ignore rules, and agent operating rules. Verification: initial repository commit and remote verification are recorded in Git history after this documentation set is committed.
- [x] Rechecked official rules, overview, resources and submission requirements on September 26, 2026; recorded deadlines, delivery obligations and the substantive Nebius/NVIDIA requirement in the [foundation audit](docs/foundation-completion-audit.md#phase-0-dated-compliance-review). Future rechecks remain mandatory under the standing rule above and Phase 11.

## Phase 1 — Hackathon stack discovery

**Status: complete for the project foundation.** The Phase 1 exit gate remains passed. Account/provider unknowns remain explicitly unverified in the separate non-blocking provider-operations follow-up below; they do not reopen Phase 1 or block Phase 3.

- [x] Selected `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory for the first semantic-coverage proof of concept. Rationale: Nebius documents it as currently available through an OpenAI-compatible API and optimized for complex reasoning/instruction following; it is a deliberately provisional interactive-classification choice, not a benchmarked production decision. See `experiments/README.md`.
- [x] Built and live-ran a small comparison across all four NVIDIA model IDs returned by the authenticated Token Factory catalog on September 16, 2026. Reused the unchanged POC cases, prompts, generation settings, and validator for three rounds (48 requests). Recorded correctness, full-response latency, provider token usage, and failures in [the benchmark report](experiments/BENCHMARK.md). Super passed 12/12 (1.370 s mean), Nano 11/12, Ultra 6/12, and Lightning 0/12; all failures hit the original 300-token cap. Keep Super provisionally for this contract. This does not complete representative quality, throughput, pricing/credits, or production selection work.
- [x] Recorded the project owner's authenticated model-access test, one-off successful Super inference, and observed 404/422/timeout/401 failures in the [Phase 1 stack discovery record](docs/phase-1-stack-discovery.md). Selected Token Factory + Super for current semantic coverage and deferred extra deployment infrastructure. The one-off 3.520170 s request is separate from the 1.370 s semantic-benchmark mean; future timeout state/control behavior is not yet implemented.
- [x] Read official Nebius Token Factory documentation and public model cards on September 17, 2026; recorded dynamic quotas, billing/credit rules, four-model prices and hosted context windows, API constraints, privacy/availability limitations, documentation conflicts, and workload cost/capacity estimates in the [Token Factory operating constraints](docs/phase-1-token-factory-constraints.md). Verification: sources and model detail cards inspected, benchmark-derived arithmetic recomputed, and document links checked. This is public-documentation evidence, not account quota or billed-cost verification.
- [x] Authenticated billing evidence confirmed minimal actual usage and sufficient provisioned credits for the experiment. This is observed billing evidence for the cost/credit portion of the exit gate, not a retrospective estimate; previously inspected private account evidence is not included in the public repository.
- [x] Investigated Token Factory, Serverless Jobs, Serverless Endpoints, DevPods/current Devlabs and explicit-compute alternatives against current official sources. Recorded use cases and reasons to retain hosted inference without provisioning infrastructure in the [foundation audit](docs/foundation-completion-audit.md#phase-1-infrastructure-investigation).
- [x] Evaluated the authenticated Nano, Super and Ultra routing keys on extraction, longer-transcript coverage and simple reminder selection: 54 live synthetic requests, two rounds. Super and Ultra each passed 18/18; Nano passed 14/18. Recorded latency, usage, failures and the limits of these discovery tasks in the [workload trial](experiments/FOUNDATION-TRIAL.md).
- [x] Mapped ingestion to deterministic normalization, extractive concepts and semantic judgments to provisional Super inference, reminders to simple selection initially, ASR to a separate speech component investigation, and embeddings to no current requirement. See the [workload assignment](docs/foundation-completion-audit.md#workload-assignment-and-model-candidates); this does not select or implement a Phase 3 provider.
- [x] Prototyped and measured three workloads across 54 model-comparison calls, followed by a 45-call scheduled load trial and eight selected-Super context-reservation probes. Recorded latency, quality, serial throughput, queue delay, the tested 262,144-token combined reservation boundary, usage-based estimates and minimal observed actual usage/billing. The five-second load target failed one of 36 deadlines; that failure is preserved and does not authorize reliable five-second live use. See [measurements and limits](experiments/FOUNDATION-TRIAL.md). Full-context generation and undocumented provider/account semantics remain in the explicit follow-up above.
- [x] Documented the substantive Token Factory → NVIDIA inference path and provisional Super selection. The [measured trade-offs](experiments/FOUNDATION-TRIAL.md#decision-and-remaining-work) support the next bounded live-use experiment, not a production-readiness claim: Super passed all cases at about one-quarter of Ultra’s estimated cost, while Ultra was faster. Remaining provider-operations questions are non-blocking follow-up.

**Exit gate — PASSED:** Repeatable requests verify required Nebius authentication and NVIDIA model access. Relevant API contracts and failure behavior are documented. The Super benchmark provides 12/12 correct/valid results with a 1.370-second mean latency, and authenticated billing evidence confirmed minimal observed usage for the compared activity. Together these preliminary latency and observed cost/credit results justify the next workload experiment. The September 26 workload comparison, scheduled load, context-reservation checks and infrastructure review extend this evidence. Account/provider unknowns remain explicit in the non-blocking follow-up below; full production capacity, privacy and reliability claims are not established.

### Non-blocking provider-operations follow-up (outside the Phase 1 completion checklist)

- Confirm effective RPM/TPM and quota scope, including aggregation, reservation and burst semantics.
- Confirm grant expiry, eligible services and credit-consumption order; account balances and transaction details remain intentionally omitted from public documentation.
- Confirm exact served context/output ceilings and model-specific API behavior, including the prompt-accounting discrepancy.
- Reconcile provider prompt accounting with returned usage and validate production-scale reliability before making capacity or live-session claims.

These questions remain open operational evidence. They do not make Phase 1 incomplete and do not block Phase 3 progression.

## Phase 2 — Presentation representation

- [x] Reconciled this investigation with the existing [source-format and suitability decision](docs/phase-2-presentation-representation.md#source-decision-and-suitability): authorized Google Slides REST first, PPTX as a future adapter candidate, PDF deferred. Rechecked the Google read contract and user-data policy on September 26; no additional format support is claimed.
- [x] Selected Google Slides as the first supported source per the owner decision, with PPTX retained as a future adapter and PDF deferred. Compared structural/note/revision access and recorded OAuth prerequisites, official API terms/data-use constraints and hackathon compatibility in the [Phase 2 design](docs/phase-2-presentation-representation.md). This selection does not establish public OAuth readiness or live presentation control.
- [x] Established `PresentationSource.ingest(...) -> Deck` with a Google Slides REST adapter and a pure normalizer. Provider dictionaries stay inside the adapter; downstream representation/comparison uses only the internal model. Verified through deterministic and mocked transport/CLI tests.
- [x] Added source-grounded concept drafts over the existing text/structure/notes ingestion. Three synthetic engineering/business/education decks exercise nested groups, notes and repetition; Super extracted the expected concepts in all six live trials. Drafts retain exact source support and snapshot identity, require presenter review, and do not change schema 1.0 ingestion or coverage state. See the [workload trial](experiments/FOUNDATION-TRIAL.md) and [audit](docs/foundation-completion-audit.md#phase-2-source-formats-and-edge-cases).
- [x] Defined schema 1.0 for decks, slides, normalized elements/groups/tables, speaker notes, provenance and source revisions. `SourceRevision` contains only optional `revision_id` and `fetched_at`. A concept shape is reserved; ingestion explicitly emits `not_extracted` with no generated concepts or invented confidence. Verified serialization, references, schema and fingerprint invariants.
- [x] Preserved source presentation/page/object identifiers as provenance, ordered slides, direct text/structure and notes. Internal IDs are snapshot-local; Google IDs are not permanent identities. Explicit issues document unsupported visuals, inherited content and normalization limits. Verified with synthetic fixtures; live source verification remains below.
- [x] Ingested an owner-controlled eight-slide Google Slides fixture on September 25, 2026 and verified the baseline against a second read-only source fetch: 189 field assertions passed for provenance, ordered source IDs, direct text, notes, a 2×3 table, image alt text and group children. Sparse content and duplicate fingerprints were verified, revision metadata matched, and source replay reproduced the snapshot exactly. Private baseline artifacts remain ignored. See [live baseline evidence](docs/testing/presentation-representation.tdd.md#live-baseline-evidence--september-25-2026) for limitations; no source mutation occurred.
- [x] Implemented deterministic snapshot comparison: retained source IDs first, then unique substantive-content fingerprints among unmatched slides; duplicates remain ambiguous. Relative-order changes are separate from insertion/deletion position shifts. Content/notes changes invalidate concept reuse, source-reference changes require rebinding, incomplete extraction requires review, and no live coverage carryover is authorized. Full persistent/fuzzy identity is deferred. Behavior is documented and tested.
- [x] Added 30 deterministic tests for representation, normalization, snapshot comparison, malformed input, API failures and CLI output. All 41 repository tests pass. Tests cover optional/changed revision tokens, reorder, notes edits, replacement IDs, duplicate ambiguity and merged tables. See [test evidence](docs/testing/presentation-representation.tdd.md); these are offline results, not live ingestion evidence.
- [x] Verified the owner-approved live mutation/reorder pass against the saved baseline: seven matches (six source-ID, one content-fingerprint), two content changes for separate text/notes edits, one addition, one removal and detected reorder. Verified duplicate-then-replace content before deleting the original; correspondence requires rebinding, not persistent identity. Preserved the live duplicate pair and separately verified two-by-two ambiguity with page-ID hints withheld in memory. Revisions changed; snapshots/source reports stayed ignored and owner-only; no coverage state transferred. All 41 tests passed on rerun. See [mutation evidence](docs/testing/presentation-representation.tdd.md#live-mutationreorder-evidence).
- [x] Evaluated sparse/blank content, images/charts/diagram markers, repeated concepts, reorder, presenter notes, table cells and nested groups using existing live evidence plus new deterministic/live-synthetic tests. Recorded supported handling and explicit limits in the [edge-case matrix](docs/foundation-completion-audit.md#phase-2-source-formats-and-edge-cases). All 97 repository tests pass; the new extraction module has 97.6% statement coverage. Visual understanding remains explicitly unsupported.

**Exit gate — PASSED:** An owner-controlled representative deck was ingested through the Google Slides adapter into schema 1.0, with source-checked content, notes, identifiers, order and provenance. The baseline passed 189 field checks; a second live snapshot verified the approved reorder, edits, addition/removal and replacement-ID case. All 41 deterministic tests pass, and duplicate fallback ambiguity was verified separately in memory while preserving the live pair. Unsupported content is identified explicitly. This gate establishes the bounded representation foundation and the Phase 2 checklist is complete.

**Phase 2 checklist complete — September 26, 2026:** ingestion investigation, extractive concept prototype and bounded edge-case evaluation are now verified. The live Google fixture still contains only one group level; nested groups were verified synthetically. Other source adapters, full persistent identity and visual understanding remain explicitly unsupported extensions, not requirements silently checked off here. The earlier foundation was approved through PR #4. Phase 3 is the next active phase; provider-operations follow-up remains openly unverified without invalidating the completed Phase 1 foundation.

## Phase 3 — Speech capture and transcription

**NEXT ACTIVE PHASE.** The Phase 0–2 foundation is complete. The verified work below is retained; the remaining Phase 3 gate work is now the active roadmap focus.

- [x] Investigated host audio capture and privacy controls for the provisional Deepgram POC. Confirmed PipeWire/PipeWire-Pulse/WirePlumber, selected the unmuted Realtek ALC294 default source, proved non-silent in-memory capture, and identified the required 48 kHz stereo to 16 kHz mono conversion. Authenticated Nova-3 streaming and `mip_opt_out=true` were accepted in a bounded live request; exact balance/credit origin remains unavailable because the key lacks billing scope. See the [implementation/preflight evidence](docs/phase-3-transcription-options.md#implementation-and-preflight-evidence--september-27-2026).
- [ ] Prototype streaming transcription and measure delay, accuracy, partial-result stability, and failure behavior in realistic presentation conditions.
- [x] Compared four realistic transcription paths against current official documentation and transcript schema 1.0. Selected Deepgram Nova-3 monolingual streaming provisionally for the first live POC because it exposes real interim/final behavior with minimal setup and a zero-content-retention option. The subsequent fixed-budget review retains that choice, prioritizes open Parakeet/NeMo as the NVIDIA challenger, and retains Speech NIM as a later candidate conditional on entitlement. This investigation did not capture audio or select a production provider; see the [component investigation](docs/phase-3-transcription-options.md).
- [x] Investigated Speech NIM on Cloud/Serverless and open NVIDIA streaming models against the owner's $100 Cloud maximum through October 30. Documented explicit runtime/storage arithmetic, a proposed $40 ASR ceiling/$30 other-work allowance/$30 safety reserve, and unverified account/license/streaming details. Bounded usage can fit; continuous GPU hosting cannot. Official judge-access obligations extend through December 15 and still require a feasible access plan. See the [budget addendum](docs/phase-3-transcription-options.md#fixed-budget-nebiusnvidia-addendum). No infrastructure or inference was run; owner review precedes implementation.
- [x] Define a transcript representation covering partial versus final segments, timestamps, ordering, corrections/revisions, and speaker/session boundaries, with explicit degraded behavior for delayed, missing, or failed transcription. Implemented independently versioned schema 1.0 events and a transcript-only accumulator, with adapter-owned internal sequence/revision counters, canonical UTC start timestamps, atomic transition rejection, and explicit availability/failure history. Verified offline; see the [Phase 3 contract](docs/phase-3-speech-transcription.md).
- [x] Provide a deterministic mock/replay transcript input path using the same representation so downstream coverage and state work can proceed without live microphone input. The ten-event synthetic fixture verifies partial/final corrections, ordering, boundaries and degradation through the same accumulator. All 74 repository tests pass (41 existing, 33 new); see [test evidence](docs/testing/transcript-replay.tdd.md). No downstream coverage integration was added.
- [x] Implemented the bounded experimental Deepgram adapter and in-memory PipeWire-Pulse/WebSocket harness without changing `TranscriptEvent` 1.0. Deterministic tests cover initial/revised/final callbacks, shorter finals, timestamps, no-ops, malformed input, failure, reconnect, old-stream rejection and counter ownership. Real connectivity and disconnect/reconnect preflights passed; the three scored spoken trials remain outstanding.

**Exit gate:** A realistic live transcription trial records delay, accuracy, partial-result stability, and failure behavior. A deterministic replay verifies segment ordering, revisions, boundaries, and degraded behavior through the same downstream input contract. Document the investigated transcription choice and trial limitations.

**Current status:** The contract, deterministic replay, Deepgram adapter, local capture path, privacy-request settings, authenticated connectivity and transport reconnect are verified. The Phase 3 exit gate remains incomplete: realistic near-field, presentation-distance/noise and spoken disconnect trials have not yet produced the fixed accuracy/latency/revision evidence. Exact Deepgram balance/free-credit origin also remains unavailable, although accepted billable preflights establish usable current service without a billing action. No production provider is selected, and preflight silence/noise is not representative transcription evidence.

## Phase 4 — Semantic slide coverage

- [x] Defined the first proof-of-concept criterion: a concept is covered only when the transcript communicates its semantic meaning; paraphrases count, and keyword-only mentions do not. The model prompt and strict output contract enforce this criterion for the fixed experiment.
- [x] Built and live-verified `experiments/semantic_coverage.py`, which sends a slide title, three required concepts, and a transcript to `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory. It requests JSON and validates exact concept IDs/statuses plus `slide_complete` locally.
- [ ] Establish confidence thresholds, ambiguity handling, correction/override behavior, and evidence retention.
- [x] Created and ran four controlled cases against the live model: paraphrased one-concept coverage, keyword-only mention, two-of-three coverage, and all-concepts coverage. All returned the expected statuses; this is a qualitative smoke check, not a representative false-positive/false-negative measurement. Results are recorded in `experiments/README.md`.

The experiment's binary `covered` / `not_covered` contract is intentionally narrow; it is not the complete product state schema or production architecture. The following work extends evaluation and defines the product-facing contract.

- [ ] Define and document acceptance thresholds for semantic-coverage false-positive and false-negative behavior for checklist/guidance use before the broader evaluation is used as Phase 4 gate evidence; separate, stricter automatic-advancement thresholds remain governed by Phase 7.
- [ ] Create a broader representative evaluation set with expected judgments, including paraphrases, keyword-only mentions, ambiguous speech, and transcript corrections; measure false-positive and false-negative behavior.
- [ ] Define and test product-facing coverage outputs that retain useful supporting evidence and confidence/uncertainty, distinguish unresolved ambiguity from established coverage, and support corrections and presenter overrides.
- [ ] Associate judgments with their session, slide/source revision, and transcript context so stale or out-of-order model results cannot incorrectly change current state; verify this contract with the Phase 5 state transitions.

**Exit gate:** The broader evaluation reports false-positive/false-negative results against documented acceptance thresholds for checklist/guidance use. Repeatable cases verify evidence, uncertainty, ambiguous speech, corrections/overrides, and rejection of stale results. These results do not authorize automatic advancement.

## Phase 5 — Live presentation state and checklist

- [ ] Define the simplest justified real-time session state model for deck, current slide, transcript window, concept states, confidence/evidence, and presenter overrides; introduce persistence or a database only for a demonstrated need.
- [ ] Investigate, select, and document the first presentation environment/integration for observing current-slide state; define its source of truth and how manual slide changes are observed and reconciled.
- [ ] Define state transitions/events and update ordering for session start/end, transcript revisions, coverage results, presenter overrides, manual slide changes, and source revisions; specify correction/reversal and stale asynchronous result handling.
- [ ] Build the live checklist behavior and verify state updates, reversals/corrections, and recovery after interruptions.
- [ ] Add deterministic state-transition/replay tests for ordered and out-of-order updates, manual slide changes, overrides, corrections, and interruption/recovery; define what is restored, reset, or requires presenter action.
- [ ] Design privacy-aware handling and retention of audio, transcripts, and slide content.

**Exit gate:** Deterministic replays produce expected session/checklist states across corrections, overrides, manual slide changes, stale results, and interruption/recovery. A trial with the selected integration confirms current-slide synchronization against its documented source of truth, with explicit behavior when synchronization is lost.

## Phase 6 — Presenter guidance

- [ ] Prototype concise, non-distracting guidance derived from uncovered concepts and recent speech.
- [ ] Verify that covered topics are suppressed and important omissions are prioritized without inventing unsupported advice.
- [ ] Evaluate timing, usefulness, interruption cost, and presenter-controlled settings.
- [ ] Define a guidance output contract tied to current slide/concept evidence, with length/distraction limits, measurable timing/latency targets, and behavior under uncertainty or stale context.
- [ ] Create deterministic or repeatable evaluation cases for omissions, already-covered topics, ambiguous coverage, and delayed results; verify unsupported advice is not introduced and outdated guidance is suppressed.

**Exit gate:** Repeatable cases demonstrate concise, evidence-grounded guidance for uncovered concepts, suppression of covered/outdated topics, and conservative uncertainty handling. A timed trial meets documented length and latency targets for the intended presenter experience.

## Phase 7 — Slide advancement

- [ ] Evaluate and document the control capabilities of the presentation environment/integration selected in Phase 5 before implementing automatic control; use that integration for control if suitable, selecting an alternative control integration only if technically necessary and preserving Phase 5's current-slide synchronization contract.
- [ ] Distinguish manual control, suggested advancement, and automatic advancement; validate manual/suggested behavior before enabling automatic operation.
- [ ] Define a conservative advancement policy using coverage confidence, minimum dwell time, active-slide verification, and explicit override modes.
- [ ] Prototype presentation-environment control and test manual control, stale state, user-driven slide changes, control failures, and recovery.
- [ ] Measure accidental-advance risk and require an acceptable safety threshold before enabling automatic operation.

**Exit gate:** Manual and suggested advancement are verified in the selected environment, including stale state, user-driven changes, failure, and recovery. Record the permitted mode for integration. Automatic advancement remains disabled unless its documented safety criteria and accidental-advance threshold are verified; a manual/suggested mode may proceed to the MVP while that work remains open.

## Phase 8 — Integrated MVP

- [ ] Integrate only ingestion, speech, semantic coverage, state, guidance, and control components that have passed their applicable earlier gates, using the verified permitted control mode.
- [ ] Provide a usable end-to-end live-presentation flow with observability and graceful degradation.
- [ ] Test the MVP on representative decks and speaking styles.
- [ ] Run and record an end-to-end acceptance scenario: ingest a representative presentation into the internal deck model; start a session; feed live or replayed transcript segments with expected concept coverage; verify semantic judgments update the checklist/state and generate guidance for an uncovered concept; exercise the permitted control mode and verify current-slide state follows the presentation. Inject at least one component failure, such as an inference timeout, and verify degraded status is visible, unsupported coverage/advancement does not occur, and documented recovery or safe manual continuation works.

**Exit gate:** The recorded scenario passes with expected coverage/checklist outcomes, relevant guidance, synchronized current-slide state, the permitted control mode, and safe failure handling. Evidence identifies the deck, transcript path, component/gate versions, observed timing, and remaining limitations; replay acceptance does not replace Phase 3's live transcription verification.

## Phase 9 — Reliability and evaluation

- [ ] Measure accuracy, false coverage detection, missed coverage, end-to-end latency, advancement mistakes, resource consumption, and cost.
- [ ] Test model, network, microphone, parser, and presentation-control failures; document fallback behavior.
- [ ] Resolve the highest-risk findings and preserve repeatable evaluation instructions/results.

## Phase 10 — Hackathon-ready product

- [ ] Polish the coherent presenter experience and accessibility/usability details supported by testing.
- [ ] Deploy or package a working demo/test build on a permitted Nebius-backed path.
- [ ] Confirm the required NVIDIA model and Nebius service are demonstrably meaningful parts of the functioning product.

## Phase 11 — Submission preparation

- [ ] Review the public repository for completeness, license visibility, secret exposure, setup reproducibility, and source/assets needed to run.
- [ ] Finalize README setup/run instructions and explicit explanations of NVIDIA model use, Token Factory acceleration, and other Nebius services.
- [ ] Make a working demo URL, hosted application, or free test build available to judges as required.
- [ ] Prepare the project description, track selection, provider feedback, and any required explanation of work completed during the submission period.
- [ ] Produce and publish a public demonstration video of three minutes or less showing the product functioning.
- [ ] Perform a final official-rules and licensing/compliance review before submitting.

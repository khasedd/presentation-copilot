# Presentation Copilot roadmap

`roadmap.md` is the authoritative engineering roadmap and verified historical record for Presentation Copilot. External planning/task systems, including Career OS, may derive tasks from it but must not introduce a competing technical sequence. Checked items describe completed, verified work only; unchecked items remain planned work or investigation. The official [Devpost rules](https://nebiusglobalaihackathon.devpost.com/rules) remain the controlling compliance source.

Phases may overlap or proceed partly out of order when the technical rationale is documented, as with the isolated Phase 4 proof of concept. Gates below define the minimum verified readiness for downstream integration, not completion of every future optimization. Record gate evidence and remaining limitations before relying on a component; passing a gate does not complete unchecked work automatically.

## Phase 0 — Project definition and hackathon foundation

- [x] Explored multiple possible Project 1 ideas and selected/locked Presentation Copilot as Project 1.
- [x] Defined the speech-aware presentation-tracking concept: semantic slide coverage, a live covered/uncovered checklist, adaptive AI-assisted speaker notes, and eventual conservative automatic advancement.
- [x] Considered overall feasibility, distinguished resume/demo scope from a future production-quality system, and considered infrastructure cost.
- [x] Selected the Nebius x NVIDIA Global AI Hackathon as the foundational project context, targeted the Best Apps and Agents Track, and made substantive Nebius plus NVIDIA open-source AI use a permanent constraint.
- [x] Established the initial repository documentation, secret-handling guidance, MIT license, ignore rules, and agent operating rules. Verification: initial repository commit and remote verification are recorded in Git history after this documentation set is committed.
- [ ] Recheck official rules, overview, resources, and submission requirements before every major compliance decision and before submission; update this record if they change.

## Phase 1 — Hackathon stack discovery

Stack discovery may continue alongside later engineering; broader comparisons and infrastructure exploration need not block independent prototypes.

- [x] Selected `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory for the first semantic-coverage proof of concept. Rationale: Nebius documents it as currently available through an OpenAI-compatible API and optimized for complex reasoning/instruction following; it is a deliberately provisional interactive-classification choice, not a benchmarked production decision. See `experiments/README.md`.
- [x] Built and live-ran a small comparison across all four NVIDIA model IDs returned by the authenticated Token Factory catalog on September 16, 2026. Reused the unchanged POC cases, prompts, generation settings, and validator for three rounds (48 requests). Recorded correctness, full-response latency, provider token usage, and failures in [the benchmark report](experiments/BENCHMARK.md). Super passed 12/12 (1.370 s mean), Nano 11/12, Ultra 6/12, and Lightning 0/12; all failures hit the original 300-token cap. Keep Super provisionally for this contract. This does not complete representative quality, throughput, pricing/credits, or production selection work.
- [x] Recorded the project owner's authenticated model-access test, one-off successful Super inference, and observed 404/422/timeout/401 failures in the [Phase 1 stack discovery record](docs/phase-1-stack-discovery.md). Selected Token Factory + Super for current semantic coverage and deferred extra deployment infrastructure. The one-off 3.520170 s request is separate from the 1.370 s semantic-benchmark mean; future timeout state/control behavior is not yet implemented.
- [x] Read official Nebius Token Factory documentation and public model cards on September 17, 2026; recorded dynamic quotas, billing/credit rules, four-model prices and hosted context windows, API constraints, privacy/availability limitations, documentation conflicts, and workload cost/capacity estimates in the [Token Factory operating constraints](docs/phase-1-token-factory-constraints.md). Verification: sources and model detail cards inspected, benchmark-derived arithmetic recomputed, and document links checked. This is public-documentation evidence, not account quota or billed-cost verification.
- [x] Recorded the owner's settled [Token Factory billing evidence](docs/evidence/phase-1/nebius-token-factory-billing.png): the Usage dashboard shows $0.02 total for the tested Nemotron activity, with input/output usage for Ultra, Lightning, Nano, and Super in `eu-north1`; Super input/output each display `< 0.01M` tokens and `< $0.01`. This is actual observed billing evidence for the cost/credit portion of the exit gate, not a retrospective estimate.
- [ ] Complete account-specific Token Factory follow-up: effective RPM/TPM and quota scope, credit balance/expiry/eligibility, exact served context/output ceilings, and relevant API behavior. Use the [closure checklist](docs/phase-1-token-factory-constraints.md#7-phase-1-closure-checklist); these remain important before budgeting or integrated live-session/production claims, but do not block the Phase 1 exit gate.
- [ ] Investigate relevant Nebius AI Cloud options (including Serverless Jobs, Serverless Endpoints, DevPods, and any then-permitted alternatives) without assuming deployment selection.
- [ ] Identify NVIDIA open-source model candidates and evaluate Nemotron Nano, Super, and Ultra variants for the distinct live workloads.
- [ ] Map proposed workloads—slide concept extraction, semantic coverage judgment, guidance generation, and any transcription/embedding needs—to model or non-model components.
- [ ] Prototype and measure realistic latency, quality, throughput, context limits, and credit consumption for candidate inference paths.
- [ ] Document selected Nebius/NVIDIA components, why they are substantive, and why the measured trade-offs support live presentation use.

**Exit gate — PASSED:** Repeatable requests verify required Nebius authentication and NVIDIA model access. Relevant API contracts and failure behavior are documented. The Super benchmark provides 12/12 correct/valid results with a 1.370-second mean latency, and the settled Token Factory Usage dashboard records $0.02 total for the compared activity. Together these preliminary latency and observed cost/credit results justify the next workload experiment. Further model and infrastructure comparisons, exact context-boundary testing, realistic capacity/concurrency, privacy/retention verification, and production-readiness work remain open follow-ups; gate passage does not automatically complete those unchecked items.

## Phase 2 — Presentation representation

- [ ] Investigate permitted presentation ingestion paths and supported source formats.
- [x] Selected Google Slides as the first supported source per the owner decision, with PPTX retained as a future adapter and PDF deferred. Compared structural/note/revision access and recorded OAuth prerequisites, official API terms/data-use constraints and hackathon compatibility in the [Phase 2 design](docs/phase-2-presentation-representation.md). This selection does not establish public OAuth readiness or live presentation control.
- [x] Established `PresentationSource.ingest(...) -> Deck` with a Google Slides REST adapter and a pure normalizer. Provider dictionaries stay inside the adapter; downstream representation/comparison uses only the internal model. Verified through deterministic and mocked transport/CLI tests.
- [ ] Prototype extraction of slide text, structure, speaker notes, and meaningful concepts for representative decks.
- [x] Defined schema 1.0 for decks, slides, normalized elements/groups/tables, speaker notes, provenance and source revisions. `SourceRevision` contains only optional `revision_id` and `fetched_at`. A concept shape is reserved; ingestion explicitly emits `not_extracted` with no generated concepts or invented confidence. Verified serialization, references, schema and fingerprint invariants.
- [x] Preserved source presentation/page/object identifiers as provenance, ordered slides, direct text/structure and notes. Internal IDs are snapshot-local; Google IDs are not permanent identities. Explicit issues document unsupported visuals, inherited content and normalization limits. Verified with synthetic fixtures; live source verification remains below.
- [x] Ingested an owner-controlled eight-slide Google Slides fixture on September 25, 2026 and verified the baseline against a second read-only source fetch: 189 field assertions passed for provenance, ordered source IDs, direct text, notes, a 2×3 table, image alt text and group children. Sparse content and duplicate fingerprints were verified, revision metadata matched, and source replay reproduced the snapshot exactly. Private baseline artifacts remain ignored. See [live baseline evidence](docs/testing/presentation-representation.tdd.md#live-baseline-evidence--september-25-2026) for limitations; no source mutation occurred.
- [x] Implemented deterministic snapshot comparison: retained source IDs first, then unique substantive-content fingerprints among unmatched slides; duplicates remain ambiguous. Relative-order changes are separate from insertion/deletion position shifts. Content/notes changes invalidate concept reuse, source-reference changes require rebinding, incomplete extraction requires review, and no live coverage carryover is authorized. Full persistent/fuzzy identity is deferred. Behavior is documented and tested.
- [x] Added 30 deterministic tests for representation, normalization, snapshot comparison, malformed input, API failures and CLI output. All 41 repository tests pass. Tests cover optional/changed revision tokens, reorder, notes edits, replacement IDs, duplicate ambiguity and merged tables. See [test evidence](docs/testing/presentation-representation.tdd.md); these are offline results, not live ingestion evidence.
- [x] Verified the owner-approved live mutation/reorder pass against the saved baseline: seven matches (six source-ID, one content-fingerprint), two content changes for separate text/notes edits, one addition, one removal and detected reorder. Verified duplicate-then-replace content before deleting the original; correspondence requires rebinding, not persistent identity. Preserved the live duplicate pair and separately verified two-by-two ambiguity with page-ID hints withheld in memory. Revisions changed; snapshots/source reports stayed ignored and owner-only; no coverage state transferred. All 41 tests passed on rerun. See [mutation evidence](docs/testing/presentation-representation.tdd.md#live-mutationreorder-evidence).
- [ ] Evaluate edge cases: sparse slides, diagrams/images/charts, repeated concepts, reordered slides, and presenter-authored notes; document supported handling and explicit limitations.

**Exit gate — PASSED:** An owner-controlled representative deck was ingested through the Google Slides adapter into schema 1.0, with source-checked content, notes, identifiers, order and provenance. The baseline passed 189 field checks; a second live snapshot verified the approved reorder, edits, addition/removal and replacement-ID case. All 41 deterministic tests pass, and duplicate fallback ambiguity was verified separately in memory while preserving the live pair. Unsupported content is identified explicitly. This gate establishes the bounded representation foundation, not completion of every Phase 2 item.

**Remaining work and review:** The live source has one group with two child shapes, not a group-inside-group case. Concept extraction, broader representative edge-case evaluation, other source adapters and full persistent identity remain unfinished. No Phase 3+ implementation was added. PR #4 remains unmerged for owner review.

## Phase 3 — Speech capture and transcription

- [ ] Investigate audio-capture permissions, device selection, privacy expectations, and allowed transcription components.
- [ ] Prototype streaming transcription and measure delay, accuracy, partial-result stability, and failure behavior in realistic presentation conditions.
- [ ] Define a transcript representation covering partial versus final segments, timestamps, ordering, corrections/revisions, and speaker/session boundaries, with explicit degraded behavior for delayed, missing, or failed transcription.
- [ ] Provide a deterministic mock/replay transcript input path using the same representation so downstream coverage and state work can proceed without live microphone input.

**Exit gate:** A realistic live transcription trial records delay, accuracy, partial-result stability, and failure behavior. A deterministic replay verifies segment ordering, revisions, boundaries, and degraded behavior through the same downstream input contract. Document the investigated transcription choice and trial limitations.

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

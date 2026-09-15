# Presentation Copilot roadmap

This document is both the development checklist and the verified historical record. Checked items describe completed, verified work only. Unchecked items are plans or investigations—not implementation claims. The official [Devpost rules](https://nebiusglobalaihackathon.devpost.com/rules) remain the controlling compliance source.

## Phase 0 — Project definition and hackathon foundation

- [x] Explored multiple possible Project 1 ideas and selected/locked Presentation Copilot as Project 1.
- [x] Defined the speech-aware presentation-tracking concept: semantic slide coverage, a live covered/uncovered checklist, adaptive AI-assisted speaker notes, and eventual conservative automatic advancement.
- [x] Considered overall feasibility, distinguished resume/demo scope from a future production-quality system, and considered infrastructure cost.
- [x] Selected the Nebius x NVIDIA Global AI Hackathon as the foundational project context, targeted the Best Apps and Agents Track, and made substantive Nebius plus NVIDIA open-source AI use a permanent constraint.
- [x] Established the initial repository documentation, secret-handling guidance, MIT license, ignore rules, and agent operating rules. Verification: initial repository commit and remote verification are recorded in Git history after this documentation set is committed.
- [ ] Recheck official rules, overview, resources, and submission requirements before every major compliance decision and before submission; update this record if they change.

## Phase 1 — Hackathon stack discovery

- [x] Selected `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory for the first semantic-coverage proof of concept. Rationale: Nebius documents it as currently available through an OpenAI-compatible API and optimized for complex reasoning/instruction following; it is a deliberately provisional interactive-classification choice, not a benchmarked production decision. See `experiments/README.md`.
- [ ] Read current official Nebius Token Factory documentation and validate authentication, model availability, API behavior, quotas/credits, and pricing assumptions.
- [ ] Investigate relevant Nebius AI Cloud options (including Serverless Jobs, Serverless Endpoints, DevPods, and any then-permitted alternatives) without assuming deployment selection.
- [ ] Identify NVIDIA open-source model candidates and evaluate Nemotron Nano, Super, and Ultra variants for the distinct live workloads.
- [ ] Map proposed workloads—slide concept extraction, semantic coverage judgment, guidance generation, and any transcription/embedding needs—to model or non-model components.
- [ ] Prototype and measure realistic latency, quality, throughput, context limits, and credit consumption for candidate inference paths.
- [ ] Document selected Nebius/NVIDIA components, why they are substantive, and why the measured trade-offs support live presentation use.

## Phase 2 — Presentation representation

- [ ] Investigate permitted presentation ingestion paths and supported source formats.
- [ ] Prototype extraction of slide text, structure, speaker notes, and meaningful concepts for representative decks.
- [ ] Define a versioned internal slide/concept representation with provenance and confidence.
- [ ] Evaluate edge cases: sparse slides, images/charts, repeated concepts, reordered slides, and presenter-authored notes.

## Phase 3 — Speech capture and transcription

- [ ] Investigate audio-capture permissions, device selection, privacy expectations, and allowed transcription components.
- [ ] Prototype streaming transcription and measure delay, accuracy, partial-result stability, and failure behavior in realistic presentation conditions.
- [ ] Define transcript segmentation, timestamps, speaker/session boundaries, and a safe degraded mode.

## Phase 4 — Semantic slide coverage

- [x] Defined the first proof-of-concept criterion: a concept is covered only when the transcript communicates its semantic meaning; paraphrases count, and keyword-only mentions do not. The model prompt and strict output contract enforce this criterion for the fixed experiment.
- [x] Built and live-verified `experiments/semantic_coverage.py`, which sends a slide title, three required concepts, and a transcript to `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory. It requests JSON and validates exact concept IDs/statuses plus `slide_complete` locally.
- [ ] Establish confidence thresholds, ambiguity handling, correction/override behavior, and evidence retention.
- [x] Created and ran four controlled cases against the live model: paraphrased one-concept coverage, keyword-only mention, two-of-three coverage, and all-concepts coverage. All returned the expected statuses; this is a qualitative smoke check, not a representative false-positive/false-negative measurement. Results are recorded in `experiments/README.md`.

## Phase 5 — Live presentation state and checklist

- [ ] Define the real-time state model for deck, current slide, transcript window, concept states, confidence, and presenter overrides.
- [ ] Build the live checklist behavior and verify state updates, reversals/corrections, and recovery after interruptions.
- [ ] Design privacy-aware handling and retention of audio, transcripts, and slide content.

## Phase 6 — Presenter guidance

- [ ] Prototype concise, non-distracting guidance derived from uncovered concepts and recent speech.
- [ ] Verify that covered topics are suppressed and important omissions are prioritized without inventing unsupported advice.
- [ ] Evaluate timing, usefulness, interruption cost, and presenter-controlled settings.

## Phase 7 — Slide advancement

- [ ] Define a conservative advancement policy using coverage confidence, minimum dwell time, active-slide verification, and explicit override modes.
- [ ] Prototype presentation-environment control and test manual control, stale state, failure, and recovery.
- [ ] Measure accidental-advance risk and require an acceptable safety threshold before enabling automatic operation.

## Phase 8 — Integrated MVP

- [ ] Integrate only validated ingestion, speech, semantic coverage, state, guidance, and control components.
- [ ] Provide a usable end-to-end live-presentation flow with observability and graceful degradation.
- [ ] Test the MVP on representative decks and speaking styles.

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

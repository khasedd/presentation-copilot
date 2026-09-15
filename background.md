# Presentation Copilot background

## The problem and intended user

Live presenters often need to balance explaining a slide naturally, remembering its important ideas, watching the clock, and operating the presentation. Traditional speaker notes are static: they cannot tell whether an idea has already been explained, whether a key point was skipped, or whether it is safe to move on.

Presentation Copilot is for presenters who want lightweight, real-time awareness of their own presentation. It is not intended to replace their voice, force a script, or make autonomous decisions without safeguards.

## The core loop

The eventual system will connect a presenter's speech to the current slide:

```text
speech capture → transcription → semantic understanding
      → slide-concept coverage → live presentation state
      → adaptive guidance and, conservatively, slide advancement
```

Each slide will be represented as meaningful concepts or talking points rather than a literal script. The system should recognize genuine coverage when a presenter explains an idea in different words; keyword overlap alone is inadequate. It will maintain a live checklist of covered and uncovered concepts, use that state to adapt guidance, and stop suggesting material that has already been discussed. If an important point appears omitted, it should surface a concise recovery prompt.

Automatic advancement is a later goal. It should happen only when coverage evidence, the active-slide state, and confidence thresholds are sufficiently strong. An incorrect advance interrupts a presenter, so uncertainty should favor waiting, asking for confirmation, or requiring an explicit presenter-controlled mode.

## Product boundaries

The initial product remains focused on the presentation-tracking loop. Presentation ingestion, speech capture, transcription, semantic coverage, state management, guidance, and presentation control are separate risks to validate before an integrated experience. Features such as broad knowledge retrieval, production multi-tenancy, complex databases, or generalized presentation tooling are not assumed.

## Reliability, latency, and error handling

Live use makes latency and reliability product requirements. Guidance must arrive while it is useful, not after a slide has passed. The project must measure end-to-end latency, inference throughput/cost, transcription delay, false coverage, missed coverage, and presentation-control mistakes using realistic conditions.

Models can hallucinate, over-infer, misunderstand speech, or receive incomplete transcripts. Slide extraction can be wrong; network calls can fail; and the presenter can deliberately reorder or omit content. The system should retain evidence and confidence, distinguish "unknown" from "covered," degrade gracefully when a service is unavailable, and never imply certainty it does not possess. Presentation control must default to conservative behavior.

## Hackathon foundation

Presentation Copilot is being built for the **Nebius x NVIDIA Global AI Hackathon**, currently targeted at the **Best Apps and Agents Track**. According to the current [Devpost overview](https://nebiusglobalaihackathon.devpost.com/), submissions must run on Nebius Token Factory or Nebius AI Cloud and use at least one NVIDIA open-source model. The Best Apps and Agents guidance specifically emphasizes NVIDIA Nemotron models served through Token Factory.

The intended relationship is architectural, not branding: **Presentation Copilot → Nebius infrastructure/inference → NVIDIA open-source AI models**. Nebius will provide the required inference or cloud environment; NVIDIA open-source models will supply meaningful AI processing, potentially including semantic coverage reasoning and guidance. Final production model assignments, workload allocation, and deployment components have deliberately not been selected. They must first be researched and evaluated for latency, quality, throughput, cost, context needs, and live responsiveness.

For the first isolated semantic-coverage proof of concept, the project selected `nvidia/nemotron-3-super-120b-a12b` through Nebius Token Factory. Nebius documents that model as currently available through its OpenAI-compatible API and positions it for complex reasoning and instruction following. It is a reasonable first experiment for structured semantic classification, but it is not a final model decision: this one four-case check does not establish production latency, cost, or accuracy across real presentation speech.

The official [hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules) control if sources conflict or change. The current deadline stated there is October 30, 2026, 10:00 AM Pacific Time. The roadmap treats the required public, open-source repository, functioning demo/test access, setup documentation, model/Nebius explanation, short public demo video, and provider feedback as delivery requirements from the outset.

## Why incremental development

The concept was considered feasible at resume/demo scope, but it has not been implemented. A production-quality system requires careful handling of accuracy, privacy, network failure, and user trust. The project will first isolate and measure each technical risk, then integrate only proven components into an MVP. This keeps claims grounded and makes the eventual demo reliable enough to judge.

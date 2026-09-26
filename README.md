# Presentation Copilot

Presentation Copilot is an AI-powered companion for live presentations. It is intended to listen to a presenter, compare what is being said with the current slide's intended concepts, maintain a live coverage checklist, provide adaptive speaker guidance, and—only when confidence warrants it—advance the presentation.

This repository contains planning documentation, isolated semantic-coverage experiments, a Google Slides ingestion/representation foundation, and a provider-independent transcript contract with deterministic replay. No integrated application has been implemented yet.

The project is being built for the **Nebius x NVIDIA Global AI Hackathon**, targeting the **Best Apps and Agents Track**. Its eventual architecture must use Nebius Token Factory or Nebius AI Cloud and at least one NVIDIA open-source model as substantive product components.

- [Project background and design constraints](background.md)
- [Development roadmap and verified progress](roadmap.md)
- [Operational rules for contributors and agents](AGENTS.md)
- [Semantic-coverage proof of concept](experiments/README.md)
- [Phase 1 stack discovery record](docs/phase-1-stack-discovery.md)
- [Token Factory limits, pricing, billing, and operational constraints](docs/phase-1-token-factory-constraints.md)
- [Phase 2 representation, Google Slides ingestion, and snapshot comparison](docs/phase-2-presentation-representation.md)
- [Phase 3 transcript events, accumulator, and deterministic replay](docs/phase-3-speech-transcription.md)

## Status

An isolated semantic-coverage proof of concept now verifies four controlled transcript cases through Nebius Token Factory and NVIDIA Nemotron 3 Super. It is not application architecture or a production-quality evaluation. A [Phase 1 benchmark](experiments/BENCHMARK.md) now compares all four available NVIDIA model IDs on the unchanged cases, with latency and token usage recorded. Super is the only model that passed all 12 attempts under the existing token cap. The [September 17 documentation review](docs/phase-1-token-factory-constraints.md) records public pricing, quotas, context limits, billing rules, and operational risks. Account-specific limits and credit deductions, realistic load/quality evaluation, broader stack discovery, and presentation integration remain open.

Phase 2 now provides schema 1.0 snapshots, a read-only Google Slides adapter, explicit extraction limitations, and deterministic reorder/change comparison. All 41 offline tests pass. Baseline live ingestion passed 189 source-field checks, and an owner-approved mutation pass verified reorder, text/notes edits, addition, removal and a content-preserving replacement ID. Duplicate fallback ambiguity was verified separately in memory while preserving the live pair. The Phase 2 exit gate passes; unchecked concept extraction and broader evaluation work remain open. UI and live presentation control are not part of this foundation.

Phase 3's first slice now provides schema 1.0 transcript events, strict ordering/revision and stream-boundary validation, and synthetic JSON replay through a transcript-only accumulator. All 74 repository tests pass (41 existing, 33 new). No microphone or transcription provider is implemented, and the Phase 3 gate remains incomplete. See the [contract and runnable replay example](docs/phase-3-speech-transcription.md#deterministic-replay) and [test evidence](docs/testing/transcript-replay.tdd.md).

## Google Slides prototype

Export `GOOGLE_SLIDES_ACCESS_TOKEN` locally with the `presentations.readonly` OAuth scope and access to your test deck. The CLI reads the process environment only; it does not automatically load `.env` or obtain/refresh a token. Never commit or paste real tokens.

```bash
mkdir -p presentation-output
python3 -m experiments.ingest_google_slides PRESENTATION_ID --output presentation-output/deck.json
python3 -m unittest discover -s tests -v
```

The output directory is ignored, files are created with owner-only permissions, and existing files are not overwritten. See the [Phase 2 design](docs/phase-2-presentation-representation.md) for the schema, source limitations and live verification requirements.

## License

[MIT](LICENSE)

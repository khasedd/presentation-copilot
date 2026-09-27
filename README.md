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
- [Phase 3 transcript contract, Deepgram POC, and deterministic replay](docs/phase-3-speech-transcription.md)
- [Foundation completion audit and remaining account/provider follow-up](docs/foundation-completion-audit.md)
- [Model comparison, scheduled load and context-boundary measurements](experiments/FOUNDATION-TRIAL.md)

## Status

**Phases 0–2 are complete for the project foundation, and Phase 3 is the next active phase.** Account/provider questions remain explicitly unverified non-blocking operational follow-ups; the completed Phase 1 foundation and its passed exit gate remain unchanged.

The original semantic benchmark remains intact. A new [54-request comparison](experiments/FOUNDATION-TRIAL.md) tested extraction, longer transcript coverage and reminder selection: Super and Ultra each passed 18/18; Nano passed 14/18. Super remains provisional. A subsequent 45-request scheduled trial returned all expected outputs, but missed one of 36 five-second coverage deadlines. That failed timing result is preserved. The report distinguishes minimal observed billing from reproducible experiment cost estimates and records bounded context-reservation checks.

Phase 2 retains schema 1.0 ingestion, verified live Google Slides snapshots and conservative snapshot comparison. It now also provides source-grounded concept drafts in a separate snapshot-bound artifact. Drafts retain exact supporting quotes, require presenter review, and explicitly flag unsupported or missing content. The [foundation audit](docs/foundation-completion-audit.md) covers source formats and edge-case limits. Its 97-test foundation baseline remains intact; the current Phase 3 branch passes **120 repository tests**. No integrated application, visual understanding or live control is claimed.

The Phase 3 transcript contract and deterministic replay remain available, and the current bounded branch adds a provisional Deepgram adapter plus an aggregate-only in-memory microphone trial harness. Authenticated capture/connectivity and reconnect preflights pass; the realistic scored spoken trials remain pending, so Phase 3 is not complete. See the [contract and runnable replay example](docs/phase-3-speech-transcription.md#deterministic-replay) and [POC evidence](docs/phase-3-transcription-options.md#implementation-and-preflight-evidence--september-27-2026).

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

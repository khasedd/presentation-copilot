# Presentation Copilot

Presentation Copilot is an AI-powered companion for live presentations. It is intended to listen to a presenter, compare what is being said with the current slide's intended concepts, maintain a live coverage checklist, provide adaptive speaker guidance, and—only when confidence warrants it—advance the presentation.

This repository contains planning documentation and isolated semantic-coverage experiments. No integrated application has been implemented yet.

The project is being built for the **Nebius x NVIDIA Global AI Hackathon**, targeting the **Best Apps and Agents Track**. Its eventual architecture must use Nebius Token Factory or Nebius AI Cloud and at least one NVIDIA open-source model as substantive product components.

- [Project background and design constraints](background.md)
- [Development roadmap and verified progress](roadmap.md)
- [Operational rules for contributors and agents](AGENTS.md)
- [Semantic-coverage proof of concept](experiments/README.md)

## Status

An isolated semantic-coverage proof of concept now verifies four controlled transcript cases through Nebius Token Factory and NVIDIA Nemotron 3 Super. It is not application architecture or a production-quality evaluation. A [Phase 1 benchmark](experiments/BENCHMARK.md) now compares all four available NVIDIA model IDs on the unchanged cases, with latency and token usage recorded. Super is the only model that passed all 12 attempts under the existing token cap. Broader stack discovery, representative quality evaluation, pricing verification, and presentation integration remain future work.

## License

[MIT](LICENSE)

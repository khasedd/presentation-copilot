# Presentation Copilot

Presentation Copilot is an AI-powered companion for live presentations. It is intended to listen to a presenter, compare what is being said with the current slide's intended concepts, maintain a live coverage checklist, provide adaptive speaker guidance, and—only when confidence warrants it—advance the presentation.

This is a planning-only repository foundation. No application functionality has been implemented yet.

The project is being built for the **Nebius x NVIDIA Global AI Hackathon**, targeting the **Best Apps and Agents Track**. Its eventual architecture must use Nebius Token Factory or Nebius AI Cloud and at least one NVIDIA open-source model as substantive product components.

- [Project background and design constraints](background.md)
- [Development roadmap and verified progress](roadmap.md)
- [Operational rules for contributors and agents](AGENTS.md)
- [Semantic-coverage proof of concept](experiments/README.md)

## Status

An isolated semantic-coverage proof of concept now verifies four controlled transcript cases through Nebius Token Factory and NVIDIA Nemotron 3 Super. It is not application architecture or a production-quality evaluation. Broader stack discovery, model comparison, latency/cost measurement, and presentation integration remain future work.

## License

[MIT](LICENSE)

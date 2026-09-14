# Development rulebook

## Scope and product discipline

- Read the assigned task and relevant repository documentation before changing anything.
- Keep changes small, purposeful, reviewable, and within the approved task. Do not silently expand scope or implement unrelated features.
- Preserve working behavior. Do not perform major architecture rewrites without a documented reason and explicit task authority.
- Build the roadmap incrementally: prove individual risks before combining subsystems. Do not implement speculative future features outside the current roadmap milestone.
- Prefer clear, modular interfaces and simple designs over cleverness, premature optimization, or unnecessary abstraction.
- Use descriptive names, keep modules cohesive, document non-obvious decisions, and maintain backwards compatibility when an existing public interface requires it.

## Hackathon discipline

This repository is being developed for the Nebius x NVIDIA Global AI Hackathon. All engineering decisions must remain compatible with the current official rules. Nebius infrastructure/inference and NVIDIA open-source model use must remain substantive parts of the product, not decorative integrations. Before making a major third-party service, SDK, model, dataset, or infrastructure dependency foundational, confirm its technical and legal suitability (license, terms, API/data use) and its compatibility with the current rules. Consult official Devpost, Nebius, and NVIDIA sources when uncertain. Hackathon compliance takes precedence over convenience.

## Documentation and roadmap

- Update documentation whenever completed work changes the actual project state.
- Update `roadmap.md` when a meaningful task is implemented and verified; check an item only after that verification.
- Record enough implementation context at each completed milestone to explain what changed and why.
- Record meaningful architectural decisions and their rationale near the decision or in dedicated documentation when introduced.
- Never fabricate completion, tests, performance, integrations, deployment, or compliance.

## Testing and verification

- Test meaningful behavior and run relevant existing tests before reporting a task complete.
- Add a focused regression test when fixing a bug where practical.
- Compilation, linting, or code generation alone is not proof of correct behavior.
- Verify real behavior in proportion to risk, including failure paths where relevant, and report what was actually run.

## Git and GitHub

- Inspect `git status` before work and before committing; inspect changes before staging and staged changes before committing.
- Keep commits focused and use clear, meaningful messages. Do not bundle unrelated work.
- Treat GitHub history as the truthful project record. Avoid rewriting published history and never force-push `main` without explicit authorization.
- Push completed commits promptly, verify the push and upstream tracking, and report failures honestly.
- Use feature branches and pull requests for substantive implementation work unless the task explicitly authorizes a direct `main` commit.

## Security and secrets

- Never commit credentials or sensitive values: Nebius/NVIDIA credentials, API keys, tokens, passwords, private keys, cloud or database credentials, OAuth secrets, or sensitive environment files.
- Use environment variables for runtime configuration. Local real values belong only in ignored files; committed examples contain safe placeholders only.
- Check staged changes for secrets before every commit. If a real credential enters Git history, stop and report it immediately—removing the visible file is not sufficient remediation.
- Minimize privileges, validate untrusted input, and avoid logging sensitive data. Treat audio, transcripts, presentation content, and user identifiers as potentially sensitive.

## Dependencies and architecture

- Add dependencies only when they solve a concrete, current requirement. Prefer maintained dependencies with compatible licenses and document material choices.
- Pin or otherwise manage versions reproducibly once a package manager is selected; do not install frameworks or cloud infrastructure speculatively.
- Keep provider integrations behind explicit boundaries so they can be tested, observed, and fail safely, while preserving the required substantive Nebius/NVIDIA path.
- Design presentation control conservatively: failure, uncertainty, stale state, and network degradation must not cause unsafe automatic advancement.

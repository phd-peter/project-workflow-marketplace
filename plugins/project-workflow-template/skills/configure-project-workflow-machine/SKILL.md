---
name: configure-project-workflow-machine
description: Compare and optionally install the bundled personal Global AGENTS and read-only project_scout configuration on a local Codex machine. Use when setting up a new computer or when the user asks to inspect, merge, or update user-level Codex AGENTS.md, config.toml, or project-scout.toml for this workflow.
---

# Configure machine-level workflow support

Treat user-level configuration as optional and separately approved. Never overwrite an existing global file wholesale.

## Workflow

1. Locate `assets/machine-setup` two directories above this `SKILL.md`.
2. Inspect these paths read-only: `~/.codex/AGENTS.md`, `~/.codex/config.toml`, and `~/.codex/agents/project-scout.toml`.
3. Compare them with `Global_AGENTS.md`, `config-snippet.toml`, and `project-scout.toml` from the plugin.
4. Present a path-by-path merge proposal that preserves unrelated instructions and configuration.
5. Apply only explicitly approved files or sections. Create missing parent directories only at apply time.
6. Read written files back as UTF-8 and report exact changed paths.

## Merge rules

- If global `AGENTS.md` is absent, propose copying the bundled file. If present, propose a human-readable merge; do not replace it.
- If `[agents.project_scout]` exists, compare values and propose only conflicting keys.
- Do not rewrite legacy `max_threads`; add `max_concurrent_threads_per_session` only when no concurrency setting exists.
- Keep `project_scout` read-only.
- A changed proposal requires fresh approval.

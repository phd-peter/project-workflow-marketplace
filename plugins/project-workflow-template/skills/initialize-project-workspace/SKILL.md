---
name: initialize-project-workspace
description: Initialize a new local project workspace from the bundled project template. Use when the user asks to create, initialize, bootstrap, or set up a new folder with AGENTS.md, local workflow skills, SOT, INBOX/SOURCE/WORK/OUTPUT/MEETING/KNOWLEDGE folders, and project-local SOT drift hooks.
---

# Initialize a project workspace

Use the bundled deterministic script. Do not reproduce the template manually.

## Workflow

1. Resolve the target to an absolute path and locate the plugin root two directories above this `SKILL.md`.
2. Run the platform wrapper without `--apply`:
   - Windows: `scripts/project-workflow.ps1 initialize --target <absolute-target>`
   - macOS: `scripts/project-workflow.sh initialize --target <absolute-target>`
3. If the result is `requires_migration`, stop and use `$migrate-project-workspace` instead.
4. Show the proposed files and folders, target, and returned fingerprint. State that nothing has been created.
5. Apply only after a separate explicit approval. Repeat with `--apply --expected-fingerprint <fingerprint>`.
6. Run `verify --target <absolute-target>` and report the created paths.

## Safety rules

- Treat an existing project control file as an existing workspace; never initialize over it.
- Never replace an existing SOT or project evidence.
- Do not invent or reuse a fingerprint after the target changes.
- Keep generated text UTF-8.
- Create only the bundled official placeholder SOT.
- Do not use Git or `git diff` for SOT handling.

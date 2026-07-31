---
name: initialize-project-workspace
description: Initialize a new local project workspace from the bundled project template. Use when the user asks to create, initialize, bootstrap, or set up a new folder with AGENTS.md, local workflow skills, SOT, INBOX/SOURCE/WORK/OUTPUT/MEETING/KNOWLEDGE folders, and project-local SOT drift hooks.
---

# Initialize a project workspace

Use the bundled deterministic script. Do not reproduce the template manually.

## Workflow

1. Resolve the target to an absolute path and locate the plugin root two directories above this `SKILL.md`.
2. Inspect the target and its ancestors for an existing project-level `AGENTS.md` and `SOT/SourceOfTruth.md`. If the target is inside an existing project, do not initialize a nested independent project. Use a distinct `03_WORK/WNN_yyyy-mm-dd_topic` for work within that project, or choose a sibling root for a genuinely independent project.
3. Run the platform wrapper without `--apply`:
   - Windows: `scripts/project-workflow.ps1 initialize --target <absolute-target>`
   - macOS: `scripts/project-workflow.sh initialize --target <absolute-target>`
4. If the result is `requires_migration`, stop and use `$migrate-project-workspace` instead.
5. Show the proposed files and folders, target, and returned fingerprint. State that nothing has been created.
6. Apply only after a separate explicit approval. Repeat with `--apply --expected-fingerprint <fingerprint>`.
7. Run `verify --target <absolute-target>` and report the created paths and the single initialized project root.

## Safety rules

- Treat an existing project control file as an existing workspace; never initialize over it.
- Initialize one independent project root only. Never create a project inside another project's source, work, output, meeting, knowledge, or SOT tree.
- Do not initialize by copying the plugin repository, canonical asset folder, or an existing project wholesale; use the deterministic plan and approved fingerprint.
- Never replace an existing SOT or project evidence.
- The fingerprint binds the exact target path, target state, template version, template content digest, and workflow implementation digest. Do not invent or reuse it after any of those values changes.
- Keep generated text UTF-8.
- Create only the bundled official placeholder SOT.
- Do not use Git or `git diff` for SOT handling.

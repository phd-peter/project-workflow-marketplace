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
4. If the result is `requires_migration`, stop and use `$migrate-project-workspace` instead. If it is `requires_empty_target_removal`, stop and ask the human operator to inspect and remove that exact empty directory; then generate a new plan for the now-missing target.
5. Show the proposed files and folders, target, and returned fingerprint. State that nothing has been created.
6. Apply only after a separate explicit approval. Repeat with `--apply --expected-fingerprint <fingerprint>`.
7. Run `verify --target <absolute-target>` and report the created paths and the single initialized project root.

## Safety rules

- Treat an existing project control file as an existing workspace; never initialize over it.
- The target parent must already be a real directory and the initialization target must be missing. An existing target, including an empty directory, is never swapped or replaced by initialization.
- Initialize one independent project root only. Never create a project inside another project's source, work, output, meeting, knowledge, or SOT tree.
- Do not initialize by copying the plugin repository, canonical asset folder, or an existing project wholesale; use the deterministic plan and approved fingerprint.
- Never replace an existing SOT or project evidence.
- The fingerprint binds the canonical target path, parent identity, missing target state, template version, template content digest, and workflow implementation digest. Do not invent or reuse it after any of those values changes.
- Apply creates a private sibling staging directory, immediately opens it, and performs every directory/file creation, marker write, hash, and verification relative to that directory descriptor. It then commits the missing target with a descriptor-anchored atomic no-replace rename. The marker and copied files come from the approved plan snapshot. A concurrent target/parent/source change, symbolic-link substitution, unsupported atomic operation, or cross-filesystem operation must fail closed without reporting success or overwriting/deleting external content.
- Both pre-commit and post-commit verification require every approved template file to match its exact SHA-256 and reject every file or directory not present in the approved template/standard-directory inventory (apart from the validated marker itself).
- Windows initialization apply currently fails closed because this implementation does not have an equivalent descriptor-anchored commit primitive there; use macOS or Linux for initialization.
- Do not automatically delete sibling `.project-workflow-staging-*` paths. A failed run leaves its randomized staging/recovery evidence for human inspection because path-based recursive cleanup has a replacement race. Remove a confirmed artifact only as a separate, explicitly inspected human operation.
- Keep generated text UTF-8.
- Create only the bundled official placeholder SOT.
- Do not use Git or `git diff` for SOT handling.

---
name: migrate-project-workspace
description: Audit, migrate, restore, or verify an existing local project workspace. Use when the user asks to replace or update AGENTS.md and project-local skills, preserve the old operating files in an external backup, optionally sync workflow docs or hooks, roll back a migration, or check the installed template version without changing SOT or project evidence.
---

# Migrate a project workspace

Use the bundled deterministic script. The default migration replaces only `AGENTS.md` and the complete `.agents/skills` directory after external backup.

## Audit and migrate

1. Resolve the target to an absolute path, confirm it is the existing project's single root rather than a `WNN` or another child folder, and locate the plugin root two directories above this `SKILL.md`.
2. Run the wrapper without `--apply`:
   - Windows: `scripts/project-workflow.ps1 migrate --target <absolute-target>`
   - macOS: `scripts/project-workflow.sh migrate --target <absolute-target>`
3. Add only requested options:
   - `--include-docs` for `README.md` and `HUMAN_WORKFLOW_GUIDE.md`.
   - `--include-hooks` for hook scripts and a merge that preserves unrelated hooks.
   - `--create-missing-folders` for missing standard folders.
   - `--backup-root <absolute-external-path>` when the default parent-level backup is unsuitable.
4. Present the target, external backup destination, changed components, protected paths, and fingerprint. Do not apply in the proposal response.
5. After separate explicit approval, repeat identical options with `--apply --expected-fingerprint <fingerprint>`.
6. Run `verify --target <absolute-target>` and report the backup path.

## Restore

1. Run `restore --target <absolute-target>` without `--apply`. Pass `--backup <absolute-backup>` for an older backup.
2. Show conflicts and the fingerprint.
3. Apply only after separate approval with `--apply --expected-fingerprint <fingerprint>`.
4. If files changed after migration, stop. Use `--force-conflicts` only after explicit approval to overwrite the listed conflicts.
5. Preserve the external backup after restoration.

## Invariants

- Target one project root only; never create or migrate a nested independent project inside another project.
- Never change `SOT`, `01_INBOX`, `02_SOURCE`, `03_WORK`, `03_WORKS`, `04_OUTPUT`, `05_MEETING`, or `06_KNOWLEDGE`.
- Back up before replacing and verify copied backups by SHA-256.
- Require the returned fingerprint during apply. It binds the target, selected options, external backup root, current component snapshot, template version, template content digest, and workflow implementation digest.
- Reject a backup inside the target workspace.
- Never delete or overwrite prior backups.
- Back up the entire old `.agents/skills` directory before replacement.
- Do not use Git or `git diff` for SOT handling.

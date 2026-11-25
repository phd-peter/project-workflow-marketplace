---
name: migrate-project-workspace
description: Adopt an existing SMB team project with additive team skills, or audit, migrate, restore, or verify an existing local workspace. Use when the user asks to replace or update AGENTS.md and project-local skills, preserve the old operating files in an external backup, optionally sync workflow docs or hooks, roll back a migration, or check the installed template version without changing SOT or project evidence.
---

# Migrate a project workspace

Use the bundled deterministic script. The default migration replaces only `AGENTS.md` and the complete `.agents/skills` directory after external backup.

## Adopt an existing shared team project

When a user wants to keep an existing project and use the team workflow, use `migrate --team-smb`. Run maintenance on the sharing host using the same local absolute project path each time. Team members subsequently open that project's root over SMB. Select one project, not the parent containing several projects. Confirm that other writers have paused for apply or restore.

1. Run the platform wrapper with `migrate --team-smb --target <absolute-local-project>`. Use the same explicit external `--backup-root` in plan and apply if requested.
2. Present additions, existing content being retained, any collisions, and the proposed AGENTS section. Review the human meaning of existing instructions, especially project-specific approvals. Resolve conflicting rules with the project owner before apply.
3. Apply only after a separate approval of the displayed target, plan and fingerprint, with identical options plus `--apply --expected-fingerprint <fingerprint>`. Do not switch to the default replacement migration to resolve a collision.
4. Run `verify --target <same-absolute-local-project>`. Report the backup location and anything retained that requires human review. If a new placeholder SOT was added, use the project's SOT review procedure to establish its first official state.
5. Have team members open the project from their PCs and invoke `$record-work-handoff` in their assigned work folders.

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

For a team adoption backup, restore uses the same host path and checks every changed component. If the project has since activated the SOT, edited an installed file or added material under a folder created at adoption, review the reported conflicts. Team restore preserves those changes even if `--force-conflicts` is supplied. For an interrupted maintenance operation, inspect the external backup manifest and the owner/time in `.project-workflow-team-maintenance.lock` before any retry. A rollback that reports `needs-recovery` requires comparing the listed paths with the backup before further changes.

## Invariants

- Target one project root only; never create or migrate a nested independent project inside another project.
- Team adoption may create the initial placeholder SOT only when absent and may create missing standard directories. Preserve existing project records.
- The default replacement migration must never change `SOT`, `01_INBOX`, `02_SOURCE`, `03_WORK`, `03_WORKS`, `04_OUTPUT`, `05_MEETING`, or `06_KNOWLEDGE`.
- Back up before replacing and verify copied backups by SHA-256.
- Require the returned fingerprint during apply. It binds the target, selected options, external backup root, current component snapshot, template version, template content digest, and workflow implementation digest.
- Reject a backup inside the target workspace.
- Never delete or overwrite prior backups.
- Back up the entire old `.agents/skills` directory before replacement.
- Do not use Git or `git diff` for SOT handling.

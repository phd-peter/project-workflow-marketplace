---
name: triage-project-inbox
description: Inspect, propose, approve, and apply classification of files from a project's `01_INBOX` into SOURCE, COMMUNICATION_LOG, WORK, or MEETING while preserving filenames and bytes. Use when the user asks to review, organize, classify, clean up, or move project inbox files, or gives an exact source-to-destination classification instruction.
---

# Triage Project Inbox

Treat `01_INBOX` as a temporary drop box. Separate the read-only proposal from the approved move, and never guess an ambiguous destination.

## Required Context

1. Read the closest `AGENTS.md` and `SOT/SourceOfTruth.md`.
2. Inspect only `01_INBOX`, relevant destination folder names, and the minimum file content needed to classify the items.
3. Record each source path, filename, size, and SHA-256 before proposing or moving it.
4. Treat existing files outside `01_INBOX` as out of scope unless the user explicitly includes them.

## Classification Rules

- Put external standards, reference documents, and stable supplied data in `02_SOURCE`.
- Put email, messenger, call notes, captures, and their attachments in one `02_SOURCE/COMMUNICATION_LOG/CNN_yyyy-mm-dd_topic` bundle per top-level communication item.
- Keep an attachment with its communication. Split unrelated communication items into separate `CNN` bundles.
- Put internal drafts, calculations, analysis, and editable working material in `03_WORK/WNN_yyyy-mm-dd_topic` or the existing `03_WORKS` equivalent.
- During parallel work, route each independent workstream to a distinct `WNN`; never make parallel workers share one editable work folder.
- Put formal agendas, minutes, decisions, and follow-up records in `05_MEETING`.
- Put no unissued draft in `04_OUTPUT`. Use a new `OUTNN` only after actual sending or official sharing is confirmed.
- During parallel work, only the designated `04_OUTPUT` integrator/writer may create or populate an `OUTNN`. Other workers must leave the confirmed file and evidence in their own `WNN` for handoff.
- When a file has multiple plausible roles, leave it in INBOX and show the competing destinations.

## Modes

### Propose

Use this mode for requests such as `INBOX 분류안을 보여줘`, `INBOX 정리해줘`, or other requests that do not specify exact destinations.

1. Work read-only.
2. Present one row per source item or inseparable communication bundle with:
   - source path
   - proposed destination
   - classification
   - reason
   - exact new folder name, when needed
   - source SHA-256
3. State which items remain ambiguous.
4. Do not create folders or move files before later explicit approval.

### Apply an approved proposal

Use this mode when the human approves a previously presented classification proposal.

1. Re-read every approved source path and recalculate its SHA-256.
2. Stop if a source is missing, its hash changed, a destination now conflicts, or the approval does not identify the active proposal.
3. Resolve every source and destination to absolute paths and verify they remain inside the project root.
4. Create only the approved destination folders.
5. Move each source once without renaming it.
6. Verify the destination filename and SHA-256 match the pre-move source.
7. Confirm the source path no longer exists and do not retain a duplicate in INBOX.
8. Report every applied and skipped move.

### Apply an exact direct instruction

Treat the current request itself as approval only when the human specifies both the exact source item and exact destination, for example `01_INBOX/A.pdf를 02_SOURCE/설계기준/A.pdf로 분류해`.

- Apply only those named moves without presenting another approval packet.
- Still perform the path, collision, filename, and SHA-256 checks from the approved-proposal mode.
- If the instruction names only a category but leaves the destination folder or communication date ambiguous, propose the missing details instead of moving.

## Communication Handoff

- Allocate `CNN` after the highest existing number under `02_SOURCE/COMMUNICATION_LOG`; use `C01` when none exists.
- Use the first raw communication date. Ask when the date cannot be supported; do not infer it from file modified time alone.
- Once raw evidence reaches `COMMUNICATION_LOG`, never move, rename, delete, overwrite, or edit it.
- Classification does not automatically create a summary. Use `record-project-communication` when the human asks to record or summarize material conclusions.

## Failure Policy

- Never overwrite an existing destination file.
- Never merge unrelated items because their filenames or dates look similar.
- Never delete a source to resolve a failed or partial move.
- If some approved moves succeed and another fails, stop, report the exact completed state, and propose the smallest recovery step.
- If a move would cross the project boundary, stop and request explicit direction.

## Validation

- verify the number of moved items matches the approved items
- verify every destination follows the applicable `CNN`, `WNN`, or `OUTNN` naming rule
- verify parallel workstreams use distinct `WNN` folders and any `OUTNN` write was performed by the designated integrator
- verify source and destination filenames match
- verify every destination SHA-256 matches its pre-move source
- verify moved originals no longer remain duplicated in `01_INBOX`
- verify established `02_SOURCE`, `COMMUNICATION_LOG`, `04_OUTPUT`, SOT, and HISTORY files were not modified

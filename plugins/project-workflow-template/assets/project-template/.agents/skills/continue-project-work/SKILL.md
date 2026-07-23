---
name: continue-project-work
description: Inspect and continue a single file-based project that separates INBOX, SOURCE, WORK, OUTPUT, MEETING, KNOWLEDGE, and the official SOT. Use when Codex must orient to the project, identify current state or the latest issued file, inspect needed evidence, perform scoped work safely, or propose a material SOT change through the update-project-sot approval workflow.
---

# Continue Project Work

## Required Inputs

- current project folder
- user request
- `SOT/SourceOfTruth.md`, when present

## Workflow

1. Read the closest `AGENTS.md` and `SOT/SourceOfTruth.md`.
2. For non-trivial project work, invoke the read-only `project_scout` custom agent once before broad inspection. Use its result to select the minimum relevant paths. Skip delegation for simple questions or one-command tasks; if the custom agent is unavailable, perform the same narrow inspection directly.
3. Inspect only the selected files needed for the request. Treat existing `03_WORK` and `03_WORKS` as equivalent; do not rename either for consistency alone. When communication evidence matters, inspect only the relevant `02_SOURCE/COMMUNICATION_LOG/CNN_yyyy-mm-dd_topic` folder and its `<folder-name>_summary.md` record.
4. State the purpose, current task, latest confirmed issued output, waiting items, and next action. Mark filename-based conclusions as inferences.
5. Preserve provenance:
   - keep source originals unchanged in `02_SOURCE`, including raw files in `COMMUNICATION_LOG`
   - treat dated communication summaries in `COMMUNICATION_LOG` as derived records, not as replacements for the raw evidence
   - create edited or analytical copies in the existing work folder
   - treat only confirmed sent or officially shared final results in `04_OUTPUT` as issued; do not place email bodies or messenger captures there
   - place meeting drafts in `03_WORK`, keep formal agendas, minutes, decisions, and follow-ups in `05_MEETING`, and store every officially sent or shared meeting artifact in `04_OUTPUT`
   - reference an official meeting artifact from meeting Markdown instead of duplicating the issued file in `05_MEETING`
   - treat `06_KNOWLEDGE/CANDIDATES` as non-official reusable-learning candidates, not as current project status
   - when proposing a new work or output subfolder, follow the naming rule in `AGENTS.md` and present the exact candidate name before creating it
6. Perform the smallest coherent task requested. Keep inspection and explanation requests read-only.
7. When facts, status, decisions, waiting items, or next actions materially changed, propose an SOT review copy through `update-project-sot`; never edit the official SOT directly.
8. Report changed files, verification evidence, assumptions, and the next human check.

## Failure Policy

- If the latest file is unclear, list candidates with dates, revisions, and locations; do not choose silently.
- If context is missing, reconstruct only what file evidence supports and mark the gaps.
- If an action would move, overwrite, rename, or delete files, propose the exact changes and wait for approval.
- If verification fails, keep the task incomplete and report the failed check.

## Validation

- verify every cited path exists
- verify issued-file claims against `04_OUTPUT`
- verify source originals were not modified
- separate source facts, working assumptions, and conclusions

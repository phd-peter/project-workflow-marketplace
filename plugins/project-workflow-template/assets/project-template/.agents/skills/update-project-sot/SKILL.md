---
name: update-project-sot
description: "Create, review, revise, approve, archive, apply, discard, or restore a project SOT/SourceOfTruth.md while preserving evidence and official-version history. Use whenever Codex needs to create, update, restructure, reconcile, correct, approve, reject, restore, or clean up an SOT or its pending review copy. Enforce explicit human approval before changing the official SOT."
---

# Update Project SOT

## File Layout

Use the following fixed structure:

- official SOT: `SOT/SourceOfTruth.md`
- active review copy: `SOT/REVIEW/SourceOfTruth_반영안.md`
- held review copies: `SOT/REVIEW/HOLD/yyyy-mm-dd_HHmmss_SourceOfTruth_보류안.md`
- official-version history: `SOT/HISTORY/yyyy-mm-dd_HHmmss_SourceOfTruth.md`

Only `SOT/SourceOfTruth.md` is the current official source of truth.

Files under `SOT/REVIEW` are non-official proposals.

Files under `SOT/HISTORY` are immutable snapshots that were previously official SOT versions.

Do not create daily SOT files or competing official SOT files.

## Core Rule

Never create, edit, replace, move, rename, or delete the official SOT before the human explicitly approves the complete review copy in a later message.

Treat a request to update the SOT as permission to inspect evidence and prepare a review copy. Do not treat it as permission to change the official SOT.

Bind approval to:

- the official SOT path
- the official SOT base SHA-256
- the review-copy path
- the review-copy SHA-256

If either file changes after the approval packet is presented, invalidate the approval and request approval again.

Use UTF-8 for every read and write.

## Initial SOT

The copied template may contain an uninitialized placeholder SOT. Treat it as uninitialized only when it still contains template markers such as `[프로젝트명]`, `Last updated: YYYY-MM-DD`, and bracketed example entries throughout the document.

- The human may directly replace the placeholder once. This direct human initialization does not require a review copy or history snapshot.
- When the human asks Codex to initialize it, follow the complete review-copy and approval workflow. Do not edit the placeholder official path directly.
- Do not archive the placeholder when applying the approved initial SOT because it was never an official project state.
- If some but not all placeholder markers were replaced, report partial initialization and ask the human whether to treat it as direct initialization in progress or an approval-based initialization. Do not choose silently.

## Required Inputs

Read only what is needed:

- closest project `AGENTS.md`
- `SOT/SourceOfTruth.md`, when present
- the active review copy, when present
- the user request
- evidence supporting the proposed SOT change

Separate:

- verified source facts
- confirmed project decisions
- working assumptions
- AI conclusions
- unresolved questions

Update the SOT only when a fact, status, decision, waiting item, risk, or next action materially changed.

Do not update it merely because a file exists or a timestamp changed.

## Existing Review Copy Check

Before creating or changing a review copy, inspect:

`SOT/REVIEW/SourceOfTruth_반영안.md`

Handle it as follows.

### No active review copy

Create a new review copy from the current official SOT.

### Active review copy matches the official SOT

Treat it as a stale or redundant copy.

A new SOT-update request authorizes recreating it from the latest official SOT.

### Active review copy differs from the official SOT

Do not overwrite, delete, or replace it silently.

Report:

- review-copy path
- review-copy SHA-256
- official SOT SHA-256
- whether the difference appears to be an unapproved proposal or a previously approved but unfinished application

Ask the human to choose one of the following actions:

- continue editing the existing review copy
- discard the existing review copy
- place it on hold
- apply it through the approval process

Do not begin an unrelated SOT proposal until the active review copy is resolved.

## Phase 1: Inspect

1. Read the official SOT using UTF-8.
2. Record its SHA-256 as the base SOT hash.
3. Classify it as an uninitialized placeholder, a partially initialized file, or an initialized official SOT.
4. Inspect only evidence relevant to the requested update.
5. Determine whether the official SOT materially needs to change.
6. Preserve the canonical bilingual SOT structure and useful content.
7. Preserve conflicts and unknowns instead of silently resolving them.
8. Confirm that referenced evidence paths exist.

If no material change is needed, do not create a review copy. Report why the official SOT remains current.

## Phase 2: Create the Review Copy

1. Create `SOT/REVIEW` if it does not exist.
2. Resolve any existing active review copy according to the Existing Review Copy Check.
3. When the official SOT exists, copy it byte-for-byte to:

   `SOT/REVIEW/SourceOfTruth_반영안.md`

4. Before editing, confirm that the new review-copy SHA-256 matches the base SOT SHA-256. Stop if it does not match.
5. In a separate edit step, apply the proposed changes directly to that same review-copy file so Codex displays the review-copy edit for human inspection.
6. Do not compose the completed proposal at another path and then replace or move it over the review copy.
7. Keep the official SOT unchanged.

The review copy must:

- contain the complete proposed SOT
- remain valid, readable Markdown
- preserve useful existing content and project style
- include precise evidence paths for material facts and decisions
- distinguish facts, assumptions, conclusions, and unresolved items
- be ready to become the official SOT after approval

Do not:

- place `+` and `-` diff markers inside the review copy
- create a document containing only a unified diff
- print a long unified diff or the complete SOT in chat
- modify the official SOT
- place an unapproved review copy in `SOT/HISTORY`

If no official SOT exists, create the complete proposed SOT at the review-copy path and treat the base SOT hash as absent.

## Phase 2.5: Verify the Review-Copy Change

After creating or revising the review copy and before presenting it for approval:

1. Inspect the change Codex displayed when the copied review file was edited.
2. Verify that every displayed change is intentional and supported by the request or cited evidence.
3. Record the changed sections and any unintended or unresolved differences.
4. Do not create a separate diff file or reproduce the complete SOT in chat. The edited review copy and Codex's displayed file change are the human comparison surfaces.

If no official SOT exists, report that the entire review copy is new and that no base-file diff is available.

## Phase 3: Present the Approval Packet

After preparing the review copy, report:

- official SOT path
- review-copy path
- base SOT SHA-256
- review-copy SHA-256
- concise summary of material changes
- changed SOT sections
- review-copy change-verification result
- a request to inspect Codex's displayed review-copy change and the complete review-copy file
- evidence paths
- assumptions and unresolved conflicts
- actions that will occur after approval:
  - archive the pre-update official SOT, except when the base is an uninitialized template placeholder
  - apply the approved review copy
  - verify the result
  - remove the applied review copy after successful verification

Ask the human to inspect the review copy.

Accept approval only when it is given after this approval packet and clearly refers to the review copy, for example:

- `SourceOfTruth_반영안.md 내용대로 적용`
- `이 반영안을 공식 SOT에 적용`
- `승인`

Do not accept ambiguous replies such as:

- `좋아`
- a partial comment
- a question
- approval given before the review copy was created
- approval referring to an earlier review-copy hash

Any change to the review copy invalidates earlier approval.

After revising it, calculate its new SHA-256 and present a new approval packet.

## Phase 4: Archive the Current Official SOT

After explicit approval, immediately before changing the official SOT:

1. Re-read the official SOT.
2. Recalculate its SHA-256.
3. Confirm that it matches the approved base SOT hash.
4. Recalculate the review-copy SHA-256.
5. Confirm that it matches the approved review-copy hash.
6. Stop if either hash differs.
7. If the approved base is an uninitialized template placeholder, record that no history snapshot is required and continue to Phase 5.
8. Create `SOT/HISTORY` if it does not exist.
9. Copy the complete current official SOT to:

   `SOT/HISTORY/yyyy-mm-dd_HHmmss_SourceOfTruth.md`

10. If that filename already exists, append a two-digit sequence:

   `SOT/HISTORY/yyyy-mm-dd_HHmmss_01_SourceOfTruth.md`

11. Confirm that the history copy is byte-for-byte identical to the pre-update official SOT.

Do not archive anything when the official SOT does not yet exist.

Do not continue to application if history creation or verification fails.

## Phase 5: Apply the Approved Review Copy

After the required history snapshot is verified, or after an approved uninitialized placeholder is confirmed to require no history:

1. Replace the official SOT content with the complete approved review-copy content.
2. Write the official SOT as UTF-8.
3. Do not apply additional unapproved edits.
4. Confirm that the official SOT is byte-for-byte identical to the approved review copy.
5. Run all validation checks.
6. Delete `SOT/REVIEW/SourceOfTruth_반영안.md` only after every validation check passes.

The approval packet must disclose this final review-copy deletion before approval.

If application or validation fails:

- do not delete the review copy
- preserve the history snapshot
- report whether the official SOT changed
- report the exact failure
- identify the smallest recovery action

If review-copy deletion fails after successful application, leave the file in place and report it as cleanup still required. Do not claim that the review cycle is fully closed.

## Review Copy Lifecycle

### Revise

When the human requests changes to the active review copy:

1. Modify the same review-copy file.
2. Recalculate its SHA-256.
3. Repeat Phase 2.5 for the newly displayed review-copy change.
4. Invalidate all previous approval.
5. Present a new approval packet.

### Discard

Delete the active review copy only when the human clearly requests rejection, cancellation, or disposal of that exact proposal, for example:

- `이 반영안 폐기`
- `SOT 수정 취소`
- `검토본 삭제`

Before deletion:

1. Confirm the exact review-copy path.
2. Confirm that the official SOT remains unchanged.
3. Delete only `SOT/REVIEW/SourceOfTruth_반영안.md`.
4. Report what was deleted and that it was an unapproved derived file.

Do not create a history snapshot for a discarded proposal.

### Hold

When the human wants to preserve but not apply the proposal:

1. Create `SOT/REVIEW/HOLD` if it does not exist.
2. Move the active review copy to:

   `SOT/REVIEW/HOLD/yyyy-mm-dd_HHmmss_SourceOfTruth_보류안.md`

3. Report the new path and SHA-256.
4. Keep the official SOT unchanged.
5. Treat the moved file as non-official.

A held proposal requires a new active review copy and a new approval packet before it can be applied.

### Completed

After successful application and validation:

- keep the updated official SOT
- keep the pre-update official version in `SOT/HISTORY`, except when the approved base was an uninitialized template placeholder
- remove the applied active review copy
- report the official SOT hash and history snapshot path
- leave `SOT/REVIEW` empty unless another proposal is active

## History Rules

Treat every file in `SOT/HISTORY` as an immutable record.

Never:

- edit a history file
- overwrite a history file
- rename or delete a history file automatically
- treat a history file as the current official SOT
- store unapproved proposals in history

To restore a historical version:

1. Select the history file with the human.
2. Copy it to the active review-copy path.
3. Treat restoration as a new SOT proposal.
4. Present a new approval packet.
5. Archive the current official SOT before applying the restoration.
6. Apply the same approval and validation workflow.

## Validation

After applying an approved review copy, verify:

- `SOT/SourceOfTruth.md` exists
- the official SOT is readable UTF-8 Markdown
- the official SOT matches the approved review copy before cleanup
- the history snapshot matches the pre-update official SOT, or the approved base was verified as an uninitialized placeholder and correctly skipped
- every cited local evidence path exists
- issued-output claims agree with confirmed communication and `04_OUTPUT`
- `02_SOURCE` originals were not modified
- existing `04_OUTPUT` files were not modified
- facts, assumptions, conclusions, and unresolved items remain distinct
- `현재 작업 (Current Work)`, `최신 발행본 (Latest Issued Output)`, `대기·미해결 (Waiting and Open Questions)`, and `다음 작업 (Next Actions)` agree with the supporting detailed evidence
- Korean text contains no encoding damage
- the active review copy was removed only after successful application and validation

Report:

- changed files
- official SOT SHA-256
- history snapshot path and SHA-256, or the verified reason no history was required for an uninitialized placeholder
- removed, held, or remaining review-copy path
- verification evidence
- remaining uncertainty
- next human check

## SOT Content Model

Use one human-maintained official SOT with this canonical bilingual section order:

1. `목적 (Purpose)`
2. `범위와 주요 사실 (Scope and Verified Facts)`
3. `현재 작업 (Current Work)`
4. `최신 발행본 (Latest Issued Output)`
5. `주요 결정 (Decisions)`
6. `대기·미해결 (Waiting and Open Questions)`
7. `다음 작업 (Next Actions)`

Keep transcripts, calculations, drawings, and meeting bodies in their proper source or work folders.

Record only current conclusions and precise evidence links in the official SOT.

Store reusable learning candidates separately under `06_KNOWLEDGE/CANDIDATES`; never add a knowledge-candidate section to the SOT.

## Provenance Rules

- Treat `02_SOURCE` originals as immutable.
- Treat `03_WORK` and `03_WORKS` as working material.
- Treat only confirmed sent or officially shared files in `04_OUTPUT` as issued.
- Distinguish the latest working file from the latest issued file.
- Mark filename- or timestamp-based conclusions as inferences.
- Preserve conflicting claims until the human resolves them.
- Treat only `SOT/SourceOfTruth.md` as official.
- Treat `SOT/REVIEW` as non-official.
- Treat `SOT/HISTORY` as immutable official-version history.

## Failure Policy

- If the latest state is unclear, list candidates and evidence instead of guessing.
- If sources conflict, preserve the conflict in the review copy.
- If approval is missing or ambiguous, keep the official SOT unchanged.
- If an unresolved active review copy exists, do not overwrite it.
- If the official SOT changed after the review copy was prepared, recreate or rebase the review copy and request approval again.
- If history creation fails, do not change the official SOT.
- If application validation fails, preserve the review copy and history snapshot.
- Never claim completion while the official SOT, history snapshot, or review-copy lifecycle is inconsistent.

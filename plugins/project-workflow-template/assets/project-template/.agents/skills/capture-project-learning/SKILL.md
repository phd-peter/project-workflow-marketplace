---
name: capture-project-learning
description: Extract reusable learning candidates from project evidence and draft or record them as separate `06_KNOWLEDGE/CANDIDATES/KNN_yyyy-mm-dd_topic.md` files. Use when Codex must identify transferable methods, recurring mistakes, important product changes, or template candidates without placing them in the official SOT or prematurely promoting them to a wider knowledge base.
---

# Capture Project Learning

## Required Inputs

- project `SOT/SourceOfTruth.md` for current context only
- relevant source, work, output, or meeting evidence
- user request or completed work scope

## Candidate Gate

Keep a candidate only when at least one condition is supported:

- another project is likely to reuse it
- it took meaningful effort to understand or solve
- the same error is likely to recur
- it changes an important product or design method
- standardizing it would reduce repeated work

Do not capture routine email, one-off dimensions, client-specific values, or unverified guesses as reusable knowledge.

## Modes

### Show candidates

When the user asks to show, identify, or review candidates, present drafts in chat only. State the proposed `KNN_yyyy-mm-dd_topic.md` path for each candidate and do not create files.

### Record candidates

When the user explicitly asks to record or save candidates, create or update files under `06_KNOWLEDGE/CANDIDATES`.

## Workflow

1. Read the SOT, then inspect only evidence relevant to the topic.
2. Separate project facts, reusable principles, assumptions, and unresolved questions.
3. Cite exact file paths and, when available, pages, sheets, cells, or clauses.
4. Inspect candidate filenames only to allocate the next `KNN` number or find an existing candidate about the same reusable principle.
5. Use `KNN_yyyy-mm-dd_topic.md`, where `NN` is the next two-digit sequence and the date is when the candidate was first recorded.
6. Append new evidence to the existing candidate when it supports the same principle. Create a new file when the principle or applicability is materially different.
7. Keep each candidate concise with these sections: `후보 내용 (Candidate)`, `재사용 가능성 (Reuse Potential)`, `프로젝트 근거 (Project Evidence)`, `적용 조건·한계 (Conditions and Limits)`, and `확인 필요 사항 (Open Checks)`.
8. Suggest promotion to the user's wider knowledge store only when the destination is known and the user explicitly requests it.
9. Suggest a reusable template only when repeated use is evidenced or the user explicitly asks.

## Failure Policy

- If evidence is insufficient, mark the candidate `확인 필요`; do not turn it into a rule.
- If sources conflict, preserve both claims and identify the needed decision.
- Never modify, move, or delete project originals while extracting learning.
- Never write a knowledge candidate into `SOT/SourceOfTruth.md` or an SOT review copy.
- Do not overwrite an unrelated existing `KNN` file.

## Validation

- verify each candidate cites project evidence
- verify project-specific values were not generalized
- verify assumptions and unknowns are visibly labeled
- verify the filename follows `KNN_yyyy-mm-dd_topic.md` and the stored date remains the first-recorded date
- verify SOT files were not changed
- verify no external knowledge-store file was changed without an explicit destination and request

---
name: record-project-communication
description: Record one or multiple project phone, email, messenger, and attachment items in separate `02_SOURCE/COMMUNICATION_LOG/CNN_yyyy-mm-dd_topic` bundles while preserving raw evidence; extract material conclusions, actions, changes, waiting items, and risks; and optionally draft or write the matching folder-named summary. Use when asked to save, summarize, record, or organize project communication, including several communication items supplied at once, or prepare an SOT update proposal from communication.
---

# Record Project Communication

Keep raw communication evidence permanent and make only the smallest useful derived summary. This skill may create a new communication bundle from user-supplied evidence, but does not classify existing INBOX files or update the official SOT. Use `triage-project-inbox` for existing INBOX files and `update-project-sot` for every SOT proposal.

## Required Context

1. Read the closest `AGENTS.md` and inspect `SOT/SourceOfTruth.md` when evaluating SOT impact.
2. Resolve “today” using the current local project date. When recording new evidence, inspect only the folder names under `02_SOURCE/COMMUNICATION_LOG` to allocate the next `CNN` number. When reading existing evidence, inspect only the requested `CNN_yyyy-mm-dd_topic` folder.
3. If an existing communication folder or its source files are requested but absent, report the missing path and do not create a conclusion record. Create a new folder only when the user asks to record supplied communication evidence.

## Folder and Filename Rules

- Use `CNN_yyyy-mm-dd_topic` for every communication bundle. Assign the next number after the highest existing `CNN` number within `COMMUNICATION_LOG`; use `C01` when none exists.
- Use the date of the bundle's first raw communication. Use the current local project date only when the user identifies the communication as today's; if the source date cannot be determined, request it instead of guessing.
- Write `topic` primarily in Korean as a short, searchable noun phrase. Preserve the original spelling of project names, customer names, specification names, and technical abbreviations, and use underscores instead of spaces.
- Include `오전` or `오후` in `topic` only when separate sessions of the same subject need distinction.
- When one request contains multiple top-level communication items, treat each item as a separate bundle and assign a separate `CNN` folder by default. Combine items only when the user identifies them as the same communication or one item is an attachment or continuation belonging to another item.
- A bundle may contain its raw message and related attachments. Keep those attachments with that communication rather than creating unrelated bundles for them.
- Preserve supplied files byte-for-byte with their received filenames. When the user pastes text with no source filename, save it as `원문.txt` in UTF-8 exactly as supplied. Do not add a heading or metadata, correct spelling, normalize wording, paraphrase, omit content, or change the order. If one bundle contains multiple separately pasted raw texts, use `원문_01.txt`, `원문_02.txt`, and later values in supplied order.
- Never rename, move, delete, overwrite, or edit raw email, messenger, capture, call-note, or attachment files.
- Write the conclusion record as `<folder-name>_summary.md`.
- Update an existing conclusion record only for additional evidence in the same communication bundle. Create a separate `CNN` folder for an unrelated subject.

## Modes

### “이 소통 내용들을 각각 기록해줘”

Split the supplied evidence by top-level communication item, allocate one `CNN` bundle per item by default, and save each raw item without alteration. For each bundle independently, write `<folder-name>_summary.md` only when the evidence contains at least one decision, action, scope/schedule/technical/financial change, waiting item, or risk. Do not create a summary for greetings or routine progress sharing.

### “오늘 소통 정리해줘”

Read the requested source bundle and present a conclusion-record draft in chat only. State the exact proposed output path, but do not write a file.

### “오늘 소통 정리해서 기록해줘”

Read the requested source bundle and write the matching conclusion record in UTF-8 only when it contains at least one decision, action, scope/schedule/technical/financial change, waiting item, or risk. If it contains only greetings or routine progress sharing, do not create a record; report that no material conclusion was found.

### “SOT 반영안 보여줘”

Identify only material current-state changes from the dated summaries and hand the request to `update-project-sot`. That workflow must copy the official SOT to the active review path, edit only the review copy so Codex displays the change, verify the exact comparison, and present one approval packet. Do not run a separate SOT or diff process here.

## Summary Content

Use only sections supported by the evidence:

```md
# <folder-name> summary

## Conclusion
- [decision, action, change, waiting item, or risk supported by the evidence]

## 근거 원문
- `[같은 폴더의 원문 경로]`

## SOT update needed
- [yes or no] — [reason]
```

Label phone notes and unconfirmed reconstructions as `기록자 메모` or `상대 확인 전`. Distinguish verified source facts, working assumptions, and AI conclusions. Do not record irrelevant greetings or routine status sharing.

When communication confirms that a meeting artifact was sent or officially shared, keep the exact issued artifact in a new `04_OUTPUT/OUTNN_yyyy-mm-dd_topic` folder. During parallel work, only the designated `04_OUTPUT` integrator/writer may perform that write; other workers must hand off the artifact and supporting evidence from their distinct `WNN`. Keep meeting records in `05_MEETING` and reference the issued path from meeting Markdown; do not duplicate the issued artifact there.

## Validation

- Confirm the number of created or selected bundles matches the number of supplied top-level communication items, except for explicitly identified attachments or continuations.
- Confirm each new folder follows `CNN_yyyy-mm-dd_topic`, uses a unique sequential number, and uses the first raw communication date.
- Confirm unrelated communication items were not merged and one communication's attachments were not split from it.
- Confirm each cited raw path exists in the inspected communication bundle.
- Confirm supplied file names and bytes are unchanged and pasted text matches the supplied text without added or removed content.
- Confirm the `<folder-name>_summary.md` filename follows the folder rule and is UTF-8.
- Confirm each bundle has a summary only when its own evidence meets the materiality threshold.
- Confirm no SOT file changed unless the separate SOT approval gate completed.
- Confirm parallel workstreams used distinct `WNN` folders and only the designated integrator wrote to `04_OUTPUT`.
- Confirm every officially sent or shared meeting artifact is stored in `04_OUTPUT` and only referenced from `05_MEETING`.

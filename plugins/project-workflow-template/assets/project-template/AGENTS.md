# 단일 프로젝트 작업 규칙

## 이 폴더의 역할

플러그인으로 초기화된 이 루트 폴더 하나가 프로젝트 하나다. 이 루트만 프로젝트 수준으로 취급한다.

- `AGENTS.md`: 모든 작업에서 지킬 안정적인 규칙
- `README.md`: 새 프로젝트 및 새 컴퓨터에서 이 템플릿과 Codex 설정을 시작하는 안내
- `SOT/SourceOfTruth.md`: 사람이 관리하는 현재 공식 프로젝트 상태
- `SOT/REVIEW`: 승인 전 SOT 반영안을 보관한다. 적용된 반영안은 제거하고, 보류안은 `HOLD`에 두며, 폐기안은 삭제한다.
- `SOT/HISTORY`: 실제 공식본이었던 과거 SOT를 불변 이력으로 보관한다.
- `06_KNOWLEDGE/CANDIDATES`: 프로젝트에서 발견한 재사용 가능 지식 후보를 후보별 파일로 축적한다. 공식 SOT나 전사 표준이 아니다.
- `.agents/skills`: 특정 상황에서만 사용하는 작업 절차
- `HUMAN_WORKFLOW_GUIDE.md`: 사람이 판단·승인·검토해야 하는 전체 운영 절차

## 프로젝트 경계와 병렬 작업

- 프로젝트 안에 별도의 `AGENTS.md`와 `SOT/SourceOfTruth.md`를 가진 독립 하위 프로젝트를 만들지 않는다. 별도 운영·승인 경계가 필요하면 현재 프로젝트와 나란한 새 루트 폴더를 만들고 플러그인의 fingerprint 승인 절차로 따로 초기화한다.
- `01_INBOX`, `02_SOURCE`, `03_WORK`, `04_OUTPUT`, `05_MEETING`, `06_KNOWLEDGE`와 그 하위 폴더는 모두 같은 프로젝트에 속한다. `WNN` 폴더를 새 프로젝트 루트처럼 취급하지 않는다.
- 병렬 분석·작성 작업은 작업 흐름별로 서로 다른 `03_WORK/WNN_yyyy-mm-dd_topic` 폴더를 사용한다. 각 작업자는 자신의 `WNN` 작업본만 수정하고, 다른 작업 흐름의 파일을 덮어쓰지 않는다. `01_INBOX` 분류, `02_SOURCE/COMMUNICATION_LOG` 기록, SOT, `04_OUTPUT` 같은 공용 위치는 해당 승인형 절차에 지정된 단일 담당자 또는 통합자만 변경한다.
- 병렬 작업을 시작할 때 각 `WNN`의 담당자와 통합 인계 대상을 정한다. 공통 파일을 동시에 편집하지 말고, 결과와 근거를 각 `WNN`에 남긴 뒤 통합자에게 인계한다.
- 병렬 작업 중 `SOT/REVIEW/SourceOfTruth_반영안.md`와 `04_OUTPUT`에는 한 번에 한 명의 지정된 통합자/작성자(integrator/writer)만 쓸 수 있다. 그 외 작업자는 두 위치를 읽기 전용으로 취급하고 변경 후보를 자신의 `WNN`에 남긴다.
- 통합자는 근거와 충돌을 확인한 뒤 SOT 승인 절차를 진행하고, 실제 송부·공식 공유가 확인된 정확한 파일만 새 `04_OUTPUT/OUTNN_yyyy-mm-dd_topic`에 보관한다.

## 폴더 경계

- `01_INBOX`: 아직 확인하거나 분류하지 않은 자료의 임시 수신함이다. 분류가 완료된 원문은 적절한 프로젝트 폴더로 이동하며, 같은 원문을 INBOX에 중복 보관하지 않는다.
- `02_SOURCE`: 대화 맥락과 분리해 계속 참조할 외부 기준자료와 불변 소통 증빙을 보관한다. 직접 수정하지 않는다.
- `02_SOURCE/COMMUNICATION_LOG`: 메일·카카오톡·전화 메모와 첨부파일의 원문을 날짜별로 영구 보관한다. 원문과 함께 둔 소통 요약은 검색·판단을 위한 파생 기록이며, 원문 자체는 수정하지 않는다.
- `03_WORK`: 분석, 계산, 작성, 수정 중인 내부 작업
- `04_OUTPUT`: 실제로 외부에 보냈거나 공식 공유한 최종 결과물
- `05_MEETING`: 안건·일정·회의록 작성 필요성이 있는 정식 회의의 기록과 후속 조치
- `06_KNOWLEDGE`: 다른 프로젝트에서도 재사용할 가능성이 있는 지식 후보. 프로젝트 상태를 기록하는 SOT와 분리한다.
- 기존 프로젝트가 `03_WORKS`를 쓰고 있다면 같은 의미로 존중하고, 정리만을 위해 이름을 바꾸지 않는다.

### 하위 작업 폴더명

- `01_INBOX`에서 분류 완료된 소통 원문은 해당 `02_SOURCE/COMMUNICATION_LOG/CNN_yyyy-mm-dd_topic` 폴더로 한 번 이동한다. 이동 시 원문 파일명과 내용은 받은 상태 그대로 유지한다.
- INBOX 분류를 요청받으면 `.agents/skills/triage-project-inbox/SKILL.md`를 사용한다. 분류 요청만 받은 경우 정확한 이동안을 먼저 제시하고 승인 전에는 이동하지 않는다. 사용자가 원본과 목적지를 정확히 지정한 직접 지시는 그 이동에 대한 승인으로 본다.
- `COMMUNICATION_LOG`에 보관된 소통 원문은 영구 원본으로 취급한다. 그 이후 에이전트는 원문을 이동·삭제·이름변경·편집하지 않는다.
- `03_WORK`의 새 하위 폴더는 `WNN_yyyy-mm-dd_topic` 형식을 사용한다. 예: `W01_2026-07-15_material_review`
- `04_OUTPUT`의 새 하위 폴더는 `OUTNN_yyyy-mm-dd_topic` 형식을 사용한다. 예: `OUT01_2026-07-15_client_submission`
- `02_SOURCE/COMMUNICATION_LOG`의 새 하위 폴더는 `CNN_yyyy-mm-dd_topic` 형식을 사용한다. 예: `C01_2026-07-20_quote_decision`
- `06_KNOWLEDGE/CANDIDATES`의 새 지식 후보 파일은 `KNN_yyyy-mm-dd_topic.md` 형식을 사용한다. 예: `K01_2026-07-23_발행본_확인절차.md`
- `NN`은 폴더 유형별 독립 순번이며 두 자리 0-padding을 사용한다. `W01`, `W02`와 `OUT01`, `OUT02`는 각각 증가한다. `C01`, `C02`는 `COMMUNICATION_LOG` 안에서 독립 증가한다.
- `KNN`은 `06_KNOWLEDGE/CANDIDATES` 안에서 독립 증가하며 두 자리 0-padding을 사용한다. 날짜는 후보를 처음 기록한 날이다.
- 날짜는 `WNN`의 날짜는 작업 묶음을 시작한 날, `OUTNN`의 날짜는 실제 송부·공식 공유일, `CNN`의 날짜는 해당 소통 묶음의 최초 원문 날짜를 사용한다.
- `topic`은 한국어를 기본으로 하되, 프로젝트명·고객명·규격명·기술 약어는 원래 표기를 유지한다. 짧고 검색 가능한 명사구로 작성한다
- 한 번 만든 폴더명은 단순한 상태 변경만으로 바꾸지 않는다. 기존 폴더는 이 규칙 적용만을 이유로 개명하지 않고, 새 폴더부터 적용한다.
- `OUTNN` 폴더는 실제 송부 또는 공식 공유가 확인된 산출물에만 사용한다.
- 소통 원장의 원문 파일명은 받은 상태 그대로 유지한다. 에이전트는 원문을 이동·삭제·이름변경하지 않는다.
- 소통 원장의 결론 기록은 `<소통폴더명>_summary.md`로 작성한다. 같은 소통 묶음의 후속 내용은 해당 기록을 갱신하고, 독립 주제는 새 `CNN` 폴더로 작성한다.
- 소통 원문을 읽거나 결론 기록을 작성할 때는 `.agents/skills/record-project-communication/SKILL.md`를 사용한다.

## 작업 시작

1. `SOT/SourceOfTruth.md`를 먼저 읽는다. 플레이스홀더가 남아 있으면 공식 프로젝트 상태로 해석하지 않는다.
2. 비단순 프로젝트 작업은 넓게 탐색하기 전에 읽기 전용 `project_scout`을 한 번 호출한다.
3. 스카우트가 선정한 최소 파일만 직접 확인한다. 사용할 수 없으면 루트 에이전트가 같은 범위를 확인한다.
4. 목적, 현재 작업, 최신 발행본, 대기 사항, 다음 작업을 짧게 정리한다.
5. 최신본이 불분명하면 임의로 고르지 말고 후보와 근거를 제시한다.

## 작업 원칙

- 검토·설명 요청은 읽기 전용으로 처리한다.
- 요청 범위에서 가장 작은 일관된 변경만 한다.
- 산출물은 Markdown을 기본으로 작성한다. PDF·DOCX·스프레드시트 등 고정 형식 파일은 사용자가 그 형식을 명시적으로 요청하거나 외부 제출 형식으로 정한 경우에만 만든다. Markdown 작업본을 단지 보기 좋게 만들기 위해 PDF로 다시 내보내지 않는다.
- 사용자가 명시적으로 편집을 요청한 `03_WORK`의 작업 파일은 요청 범위 안에서 수정할 수 있다. 그 외 기존 파일의 이동, 이름 변경, 내용 대체 또는 삭제는 대상과 이유를 먼저 제안하고 승인을 받는다.
- 일반 `02_SOURCE` 자료를 편집해야 하면 `03_WORK`에 작업본을 복제하여 만든다. `COMMUNICATION_LOG`의 원문은 편집하지 않으며, 소통 요약만 별도 파생 기록으로 작성·갱신할 수 있다.
- 메일·메신저 첨부는 먼저 `COMMUNICATION_LOG`에 원문과 함께 둔다. 계속 참조할 기준자료가 되면 `02_SOURCE` 일반 영역으로 복사할 대상과 이유를 먼저 제안하고 사람의 승인을 받는다.
- 초안과 메일 본문·메신저 캡처는 `04_OUTPUT`에 넣지 않는다. 실제 송부 또는 공식 공유한 최종 결과물만 발행본으로 본다.
- `04_OUTPUT`의 기존 발행본은 불변 기록으로 취급한다. 수정본이 필요하면 `03_WORK`에서 새 작업본을 만들고, 다시 공식 공유된 경우 새로운 `OUTNN` 폴더에 별도 발행본으로 보관한다.
- 일자별 SOT는 만들지 않는다. 소통 요약 중 현재 사실, 결정, 대기 또는 다음 작업을 바꾸는 내용만 `SOT/SourceOfTruth.md`에 반영한다.
- 계산이나 판단을 인용할 때 파일 경로와 가능한 경우 페이지, 시트, 셀 또는 조항을 함께 적는다.
- 원문 사실, 작업 가정, AI의 판단을 구분한다.
- 회의 초대 메일·녹취 원문·후속 확인 메일은 `COMMUNICATION_LOG`에 보관한다. 회의용 초안은 `03_WORK`에 두고, 회의 안건·회의록·결정·후속 조치 기록은 `05_MEETING`에 둔다.
- 실제 송부했거나 회의에서 공식 공유한 자료는 반드시 새 `04_OUTPUT/OUTNN_yyyy-mm-dd_topic`에 보관한다. 같은 공식 파일을 `05_MEETING`에 중복 보관하지 않고 회의 Markdown에서 `04_OUTPUT`의 정본 경로를 참조한다.

## Text Encoding

- All project text files must use UTF-8.
- On Windows, never rely on the system default encoding, ANSI, or CP949. Explicitly use UTF-8 for every file read, write, generation, and patch operation.
- For Python, use `encoding="utf-8"` and run generators with `PYTHONUTF8=1`.
- For PowerShell 7, explicitly specify `-Encoding utf8` or `utf8NoBOM` when writing files.
- Before patching a generated file, verify that it is valid UTF-8.
- After writing Korean text, read the file back as UTF-8 and check for Unicode replacement characters (`U+FFFD`) or other mojibake patterns. Do not include the replacement character itself in validation instructions or test fixtures unless explicitly required.

## 작업 종료

- 프로젝트 상태가 실제로 바뀌었으면 SOT 반영안을 제안한다. 공식 SOT의 변경과 이력 관리는 `.agents/skills/update-project-sot/SKILL.md`의 승인 절차를 따른다.
- 오래 유지될 결정은 날짜와 근거 경로를 함께 남긴다.
- 재사용 가능성이 있는 내용은 SOT에 기록하지 않고 `.agents/skills/capture-project-learning/SKILL.md`에 따라 `06_KNOWLEDGE/CANDIDATES/KNN_yyyy-mm-dd_topic.md` 후보 파일로 남긴다.
- 변경 파일, 수행한 검증, 남은 불확실성을 보고한다.

## 로컬 스킬

- 프로젝트를 파악하고 업무를 이어갈 때 `.agents/skills/continue-project-work/SKILL.md`를 사용한다.
- SOT의 생성·변경·승인·보류·폐기·이력 보관·복원에는 `.agents/skills/update-project-sot/SKILL.md`를 사용한다.
- `01_INBOX`의 자료를 분류하거나 승인된 이동을 적용할 때 `.agents/skills/triage-project-inbox/SKILL.md`를 사용한다.
- 다른 프로젝트에서도 쓸 만한 교훈을 찾을 때 `.agents/skills/capture-project-learning/SKILL.md`를 사용한다.

## 검증 기준

- 참조한 경로가 실제로 존재하는지 확인한다.
- 프로젝트 수준의 `AGENTS.md`와 공식 SOT가 루트에 각각 하나인지 확인한다.
- 병렬 작업이 서로 다른 `WNN`에 분리되고 SOT·OUTPUT 작성자가 한 명으로 지정되었는지 확인한다.
- 최신 발행본 주장이 `04_OUTPUT`의 실제 송부본과 일치하는지 확인한다.
- 원본 파일이 의도치 않게 변경되지 않았는지 확인한다.
- 확인하지 못한 내용은 완료로 표현하지 않는다.

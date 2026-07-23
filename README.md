# Project Workflow Marketplace

파일 기반 프로젝트의 원본·작업본·발행본·회의 기록·현재 상태를 구분하고, 사람이 중요한 변경을 승인하도록 돕는 Codex 플러그인 마켓플레이스입니다.

이 저장소의 `project-workflow-template` 플러그인은 다음을 지원합니다.

- 빈 폴더에 표준 프로젝트 구조를 만드는 신규 초기화
- 기존 워크폴더의 `AGENTS.md`와 `.agents/skills` 교체
- 교체 전 프로젝트 외부 백업과 SHA-256 검증
- 적용 이후 충돌을 확인하는 복원 절차
- 프로젝트별 SOT 변경 후보를 알리는 로컬 경고 훅

## 설치

Codex CLI에서 공개 GitHub 저장소를 마켓플레이스로 등록한 뒤 플러그인을 설치합니다.

```powershell
codex plugin marketplace add phd-peter/project-workflow-marketplace
codex plugin add project-workflow-template@project-workflow
```

설치 후에는 새 Codex 작업을 열어야 플러그인의 스킬이 로드됩니다.

업데이트가 배포되면 다음 명령으로 마켓플레이스를 갱신하고 플러그인을 다시 설치합니다.

```powershell
codex plugin marketplace upgrade project-workflow
codex plugin add project-workflow-template@project-workflow
```

## 사용

신규 폴더에서는 먼저 적용 계획을 요청합니다.

```text
$initialize-project-workspace로 이 폴더의 초기화 계획을 보여줘.
```

기존 워크폴더에서는 교체 계획을 요청합니다.

```text
$migrate-project-workspace로 이 기존 워크폴더의 AGENTS.md와 로컬 스킬 교체 계획을 보여줘.
```

이전 환경으로 돌아가려면 복원 계획을 요청합니다.

```text
$migrate-project-workspace로 최근 외부 백업의 복원 계획을 보여줘.
```

초기화와 마이그레이션은 먼저 읽기 전용 계획과 대상 fingerprint를 제시합니다. 사용자가 별도 메시지로 승인한 범위만 적용합니다.

## 안전 경계

- 기존 운영 파일은 워크폴더 바깥의 `_project-workflow-backups/<프로젝트명>/<시각>/`에 먼저 복사합니다.
- 백업과 원본의 SHA-256이 같은지 확인한 뒤에만 교체합니다.
- `SOT`, `01_INBOX`, `02_SOURCE`, `03_WORK` 또는 `03_WORKS`, `04_OUTPUT`, `05_MEETING`, `06_KNOWLEDGE`의 프로젝트 자료는 마이그레이션하지 않습니다.
- 다른 기존 훅은 보존하며, SOT 경고 훅은 공식 SOT를 자동으로 수정하지 않습니다.
- SOT 변경에는 Git이나 `git diff`를 사용하지 않습니다. 공식본을 검토본으로 복제하고 검토본만 수정한 뒤 사람의 승인을 받습니다.

## 저장소 구조

```text
.agents/plugins/marketplace.json
plugins/project-workflow-template/
  .codex-plugin/plugin.json
  skills/
  assets/project-template/
  scripts/
```

플러그인은 초기화·마이그레이션·컴퓨터 설정 스킬을 직접 제공합니다. 프로젝트 운영 스킬과 문서·훅은 각 워크폴더로 복사되므로 프로젝트가 독립적으로 작동합니다.

## 호환성

- Windows: PowerShell 7 스크립트와 훅을 실제 검증합니다.
- macOS: zsh 스크립트와 훅을 포함합니다. 현재 Windows 배포 환경에서는 macOS 실제 실행 검증이 별도 항목으로 남습니다.

현재 저장소에는 라이선스가 지정되어 있지 않습니다.

# Project Workflow Marketplace

파일 기반 프로젝트의 원본·작업본·발행본·회의 기록·현재 상태를 구분하고, 사람이 중요한 변경을 승인하도록 돕는 Codex 플러그인 마켓플레이스입니다.

이 저장소의 `project-workflow-template` 플러그인은 다음을 지원합니다.

- 빈 폴더에 표준 프로젝트 구조를 만드는 신규 초기화
- 기존 공유 프로젝트의 원본·전용 규칙·사용자 스킬을 보존하는 팀 편입 및 작업 인계
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

## SMB 공유 프로젝트에 팀 방식 적용

1. 각 PC에서 같은 버전의 마켓플레이스를 설치하고 새 Codex 작업을 연다. 로컬 배포본은 압축을 해제하고 `.agents/plugins/marketplace.json`이 있는 폴더에서 다음 명령으로 설치할 수 있다.

   ```powershell
   codex plugin marketplace add .
   codex plugin add project-workflow-template@project-workflow
   ```

2. 공유를 제공하는 PC에서 기존 자료가 들어 있는 **개별 프로젝트의 로컬 폴더**를 연다. PowerShell 7과 Python 3이 필요하다. 운영 담당자가 유지보수를 맡고 편입·복원 동안 해당 프로젝트의 작성을 잠시 멈춘다.
3. Codex에 **“$migrate-project-workspace로 이 공유 프로젝트에 팀 협업 기능을 추가할 계획을 보여줘. --team-smb를 사용해.”**라고 요청한다. 기존 지침과 추가 구역, 설치할 스킬, 보존 또는 충돌 항목, 프로젝트 외부 백업 위치를 검토한다. 대상 경로와 fingerprint를 확인하고 별도 메시지로 승인한다. 적용과 검증, 추후 복원은 호스트의 같은 로컬 경로에서 진행한다.
4. 팀원은 SMB에서 각 프로젝트의 루트를 열고 담당 작업폴더에서 작업한다. **“$record-work-handoff로 오늘 한 일과 시트에 붙일 한 줄을 정리해줘.”**라고 요청한다. 팀 시트에서 프로젝트명과 작업 ID가 같은 행을 갱신한다. 원본과 공식 상태는 프로젝트 안에 둔다.
5. 서로 다른 팀원 두 명이 각자 작업폴더에 쓴 뒤, 상대가 시트의 프로젝트 상대 경로로 근거를 여는지 확인한다. SOT 반영은 통합자 한 명이 맡고 별도 승인을 받는다.

공개 마켓플레이스와 팀 배포본의 버전이 다르면 팀에 전달된 같은 로컬 배포본을 사용한다. 플러그인 설치는 각 PC에서, 팀 편입은 프로젝트마다 한 번 진행한다.

## 사용

신규 폴더에서는 먼저 적용 계획을 요청합니다.

```text
$initialize-project-workspace로 이 폴더의 초기화 계획을 보여줘.
```

마켓플레이스 저장소, `assets/project-template`, 또는 기존 프로젝트 폴더 전체를 복사해 새 프로젝트를 만들지 않습니다. 빈 대상 루트마다 위 초기화 요청으로 계획과 fingerprint를 받은 뒤, 별도 메시지로 승인한 경우에만 적용합니다.

기존 워크폴더에서는 교체 계획을 요청합니다.

```text
$migrate-project-workspace로 이 기존 워크폴더의 AGENTS.md와 로컬 스킬 교체 계획을 보여줘.
```

이전 환경으로 돌아가려면 복원 계획을 요청합니다.

```text
$migrate-project-workspace로 최근 외부 백업의 복원 계획을 보여줘.
```

초기화와 마이그레이션은 먼저 읽기 전용 계획과 대상 fingerprint를 제시합니다. fingerprint는 정확한 대상·현재 상태·템플릿 버전·내용·실행 스크립트(마이그레이션은 옵션과 외부 백업 루트 포함)에 결합됩니다. 값이 달라지면 새 계획이 필요하며, 사용자가 별도 메시지로 승인한 범위만 적용합니다.

## 안전 경계

- 초기화된 루트 하나만 프로젝트 수준으로 사용하며, 기존 프로젝트 하위에는 독립 프로젝트를 초기화하지 않습니다.
- 프로젝트 내부의 병렬 작업은 서로 다른 `03_WORK/WNN_yyyy-mm-dd_topic`에서 수행하고, SOT 반영안과 `04_OUTPUT`은 한 번에 한 명의 지정된 통합자/작성자만 기록합니다.
- 기존 운영 파일은 워크폴더 바깥의 `_project-workflow-backups/<프로젝트명>-<경로해시8자>/<시각>/`에 먼저 복사합니다.
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

- Windows에서는 PowerShell 7 래퍼를 사용합니다. 기존 폴더에는 `migrate --team-smb`로 편입합니다. 신규 `initialize --apply`는 Windows에서 지원하지 않습니다.
- macOS에는 zsh 래퍼가 있습니다. 실제 공유 권한과 서로 다른 Windows 계정의 동시 작업은 대상 SMB에서 확인합니다.

현재 저장소에는 라이선스가 지정되어 있지 않습니다.

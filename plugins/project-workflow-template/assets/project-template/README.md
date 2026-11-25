# 프로젝트 업무 템플릿

프로젝트의 원본, 작업본, 발행본, 소통 기록과 현재 상태를 서로 혼동하지 않도록 관리하는 파일 기반 워크스페이스다.

세부 운영 규칙의 정본은 `AGENTS.md`다. 이 README는 새 프로젝트와 새 컴퓨터에서 빠르게 시작하기 위한 안내서다.

사람이 자료를 분류하고, 작업을 검토하고, 발행과 SOT 변경을 승인하는 일상 절차는 [`HUMAN_WORKFLOW_GUIDE.md`](HUMAN_WORKFLOW_GUIDE.md)를 따른다.

새 프로젝트를 만들 때 현재 워크스페이스나 로컬 참조 폴더 전체를 복사하지 않는다. 빈 대상 루트에서 `project-workflow-template` 플러그인으로 읽기 전용 계획을 만들고, 표시된 fingerprint를 확인한 뒤 별도 메시지로 승인하여 초기화한다.

## 기본 구조

```text
01_INBOX/                         아직 확인·분류하지 않은 자료
02_SOURCE/                        외부 기준자료와 불변 원본
  COMMUNICATION_LOG/              전화·메일·메신저 원문과 결론 기록
03_WORK/                          분석·계산·초안·작업본
04_OUTPUT/                        실제 송부·공식 공유한 최종 결과물
05_MEETING/                       정식 회의 안건·회의록·결정·후속 조치
06_KNOWLEDGE/CANDIDATES/          프로젝트에서 발견한 재사용 가능 지식 후보
SOT/SourceOfTruth.md              현재 유효한 상태·결정·다음 작업
.agents/skills/                   이 템플릿 전용 Codex 작업 절차
.codex/hooks/                     SOT 이후 변경 후보를 알리는 보조 검사
Global_AGENTS.md                  새 컴퓨터에 설치할 개인 전역 작업 규칙 원본
HUMAN_WORKFLOW_GUIDE.md           사람이 수행·승인·검토할 전체 운영 가이드
```

## 프로젝트 수준과 병렬 작업

- 초기화된 루트 하나가 프로젝트 하나이며 프로젝트 수준도 하나뿐이다.
- 프로젝트 하위에 별도의 `AGENTS.md`와 공식 SOT를 가진 독립 프로젝트를 만들지 않는다. 독립 경계가 필요하면 나란한 새 루트를 플러그인으로 따로 초기화한다.
- 병렬 작업은 흐름마다 서로 다른 `03_WORK/WNN_yyyy-mm-dd_topic`을 사용하고 담당자를 기록한다.
- 병렬 작업자는 자신의 `WNN`에 결과와 근거를 남긴다. `SOT/REVIEW/SourceOfTruth_반영안.md`와 `04_OUTPUT`은 한 번에 한 명의 지정된 통합자/작성자만 수정한다.
- 통합자는 작업 결과를 검증·정리하고, SOT는 승인 절차를 거치며 실제 송부·공식 공유가 확인된 파일만 새 `OUTNN`에 보관한다.

## 시작 방법 선택

0. **플러그인으로 새 폴더를 만들거나 기존 워크폴더를 교체**하려면 아래 [GitHub 플러그인 설치](#github-플러그인-설치)를 먼저 진행한다.
1. **Windows 새 컴퓨터**라면 [1. Windows 새 컴퓨터에서 시작](#1-windows-새-컴퓨터에서-시작)부터 진행한다.
2. **Codex, 전역 `AGENTS.md`, `project_scout` 설정이 이미 되어 있다면** [2. 이미 설정된 컴퓨터에서 시작](#2-이미-설정된-컴퓨터에서-시작)으로 바로 간다.
3. **macOS 새 컴퓨터**라면 [3. macOS 새 컴퓨터에서 시작](#3-macos-새-컴퓨터에서-시작)부터 진행한다.

## 팀 배포본으로 편입한 공유폴더

편입과 복원은 공유 호스트 담당자가 플러그인으로 진행한다. 팀원은 각자 새 Codex 작업에서 같은 SMB 프로젝트 루트를 열어 공유 지침을 읽는다. Python 분석 시 루트의 `requirements.txt`를 사용해 각 PC의 로컬 디스크에 프로젝트별 venv를 만든다. 각 팀원은 자신의 작업폴더에서 `$record-work-handoff`로 인계 기록과 회의 시트에 붙일 한 줄을 작성한다.

## GitHub 플러그인 설치

공개 저장소 [`phd-peter/project-workflow-marketplace`](https://github.com/phd-peter/project-workflow-marketplace)를 Codex 마켓플레이스로 등록하고 플러그인을 설치한다.

```powershell
codex plugin marketplace add phd-peter/project-workflow-marketplace
codex plugin add project-workflow-template@project-workflow
```

설치 후 새 Codex 작업을 열어야 새 스킬이 로드된다.

- 새 폴더: `$initialize-project-workspace로 이 폴더의 초기화 계획을 보여줘.`
- 기존 워크폴더: `$migrate-project-workspace로 AGENTS.md와 로컬 스킬 교체 계획을 보여줘.`
- 복원: `$migrate-project-workspace로 최근 외부 백업의 복원 계획을 보여줘.`

초기화와 마이그레이션은 먼저 읽기 전용 계획과 fingerprint를 보여준다. fingerprint는 대상·현재 상태·템플릿 버전·내용·실행 스크립트(마이그레이션은 옵션과 외부 백업 루트 포함)에 결합되므로 이 중 하나라도 바뀌면 새 계획을 받아야 한다. 사람이 별도 메시지로 승인한 경우에만 적용한다. 기존 운영 파일은 프로젝트 부모의 `_project-workflow-backups`에 복사하고 SHA-256을 검증한 뒤 교체한다. SOT와 `01_INBOX`부터 `06_KNOWLEDGE`까지의 업무자료는 마이그레이션 대상이 아니다.

## 1. Windows 새 컴퓨터에서 시작

### Codex 확인

Codex를 설치하고 로그인한 뒤 PowerShell 7에서 확인한다.

```powershell
codex --version
codex doctor --summary
```

### 개인 설정 경로 준비

```powershell
$codexHome = Join-Path $env:USERPROFILE '.codex'
$agentDir = Join-Path $codexHome 'agents'
New-Item -ItemType Directory -Path $agentDir -Force

$agentPath = Join-Path $agentDir 'project-scout.toml'
$configPath = Join-Path $codexHome 'config.toml'
$globalAgentsPath = Join-Path $codexHome 'AGENTS.md'

$agentPath
$configPath
$globalAgentsPath
```

### 개인 전역 작업 규칙 설치

프로젝트 템플릿 루트에서 다음 명령을 실행하여 `Global_AGENTS.md`를 개인 Codex 전역 규칙으로 설치한다.

```powershell
$sourceGlobalAgents = Join-Path (Get-Location) 'Global_AGENTS.md'
$targetGlobalAgents = Join-Path $env:USERPROFILE '.codex\AGENTS.md'

if (Test-Path -LiteralPath $targetGlobalAgents) {
    Write-Host "기존 전역 AGENTS.md가 있습니다. 덮어쓰지 말고 Global_AGENTS.md와 비교하여 병합하세요."
} else {
    Copy-Item -LiteralPath $sourceGlobalAgents -Destination $targetGlobalAgents
}
```

`~/.codex/AGENTS.md`는 모든 프로젝트에 적용되는 개인 작업 원칙이다. 프로젝트 폴더 안의 `AGENTS.md`는 해당 프로젝트의 구체적인 폴더 경계와 업무 규칙을 추가한다.

이후 출력된 경로에 [공통 Codex 설정](#공통-codex-설정)의 `project-scout.toml`을 만들고 기존 `config.toml`에 `[agents]` 설정을 병합한다.

전체 `config.toml`을 다른 컴퓨터에서 복사해 덮어쓰지 않는다. MCP 토큰, 개인 플러그인, 로컬 실행 경로 등 컴퓨터별 설정이 포함될 수 있다.

### 검증

```powershell
Test-Path (Join-Path $env:USERPROFILE '.codex\AGENTS.md')
codex --strict-config --version
codex doctor --summary
codex features list | Select-String 'multi_agent'
```

검증이 통과하면 Codex를 다시 시작하거나 새 작업을 열고 [업무 시작 순서](#업무-시작-순서)로 간다.

## 2. 이미 설정된 컴퓨터에서 시작

다음 조건이 이미 충족되면 설치 절차를 반복하지 않는다.

- Codex가 설치되어 있고 로그인되어 있다.
- 개인 Codex 설정에 전역 `AGENTS.md`가 설치되어 있다.
- 개인 Codex 설정에 `project_scout`이 등록되어 있다.
- `project-scout.toml`이 `read-only`로 설정되어 있다.
- `codex --strict-config --version`과 `codex doctor --summary`가 통과한다.

Windows에서는 다음 경로를 확인한다.

```powershell
Test-Path (Join-Path $env:USERPROFILE '.codex\AGENTS.md')
Test-Path (Join-Path $env:USERPROFILE '.codex\agents\project-scout.toml')
Test-Path (Join-Path $env:USERPROFILE '.codex\config.toml')
```

macOS에서는 다음 경로를 확인한다.

```bash
test -f "$HOME/.codex/AGENTS.md"
test -f "$HOME/.codex/agents/project-scout.toml"
test -f "$HOME/.codex/config.toml"
```

설정이 되어 있으면 바로 [업무 시작 순서](#업무-시작-순서)로 간다. 비단순 업무에서 `project_scout`을 따로 지시할 필요는 없다. `AGENTS.md`가 필요한 경우 자동으로 먼저 호출하도록 규정한다.

## 3. macOS 새 컴퓨터에서 시작

### Codex 확인

Codex를 설치하고 로그인한 뒤 Terminal에서 확인한다.

```bash
codex --version
codex doctor --summary
```

### 개인 설정 경로 준비

```bash
mkdir -p "$HOME/.codex/agents"

agent_path="$HOME/.codex/agents/project-scout.toml"
config_path="$HOME/.codex/config.toml"
global_agents_path="$HOME/.codex/AGENTS.md"

printf '%s\n' "$agent_path"
printf '%s\n' "$config_path"
printf '%s\n' "$global_agents_path"
```

### 개인 전역 작업 규칙 설치

프로젝트 템플릿 루트에서 다음 명령을 실행하여 `Global_AGENTS.md`를 개인 Codex 전역 규칙으로 설치한다.

```bash
source_global_agents="$PWD/Global_AGENTS.md"
target_global_agents="$HOME/.codex/AGENTS.md"

if [ -f "$target_global_agents" ]; then
  echo "기존 전역 AGENTS.md가 있습니다. 덮어쓰지 말고 Global_AGENTS.md와 비교하여 병합하세요."
else
  cp "$source_global_agents" "$target_global_agents"
fi
```

제공된 `Global_AGENTS.md`는 Windows와 macOS의 셸 규칙을 조건별로 구분하므로 두 운영체제에서 같은 원본을 사용할 수 있다.

이후 출력된 경로에 [공통 Codex 설정](#공통-codex-설정)의 `project-scout.toml`을 만들고 기존 `config.toml`에 `[agents]` 설정을 병합한다. 파일은 UTF-8을 유지할 수 있는 편집기로 작성한다.

전체 `config.toml`을 다른 컴퓨터에서 복사해 덮어쓰지 않는다. 인증정보와 컴퓨터별 경로는 새 Mac에서 별도로 설정한다.

### 검증

```bash
test -f "$HOME/.codex/AGENTS.md"
codex --strict-config --version
codex doctor --summary
codex features list | grep multi_agent
```

검증이 통과하면 Codex를 다시 시작하거나 새 작업을 열고 [업무 시작 순서](#업무-시작-순서)로 간다.

## 공통 Codex 설정

Codex 설정은 다음 세 층으로 나뉜다.

```text
개인 전역 작업 원칙  → ~/.codex/AGENTS.md
개인 Codex 설정      → ~/.codex/config.toml, ~/.codex/agents/
프로젝트 운영 규칙   → 프로젝트/AGENTS.md, SOT/, .agents/skills/
```

기존 프로젝트를 새 컴퓨터로 이전하면 프로젝트 `AGENTS.md`, `SOT`, `.agents/skills`, 설치 원본인 `Global_AGENTS.md`가 함께 이동한다. 이 이전은 새 프로젝트 초기화가 아니다. 새 컴퓨터에서는 `Global_AGENTS.md`를 `~/.codex/AGENTS.md`로 설치하고, 아래의 `project_scout`을 개인 Codex 설정에 한 번 등록한다.

이미 전역 `AGENTS.md`가 있다면 자동으로 덮어쓰지 않는다. 기존 개인 규칙을 보존하면서 `Global_AGENTS.md`의 필요한 항목만 병합한다.

### `project-scout.toml`

```toml
name = "project_scout"
description = "Fast read-only project scout for SOT review and minimum relevant-file selection before non-trivial project work."
model = "gpt-5.6-terra"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"

developer_instructions = """
Work read-only and finish quickly.

Read the closest AGENTS.md and SOT/SourceOfTruth.md first when they exist.
Inspect only directory listings, filenames, metadata, and the minimum file contents needed to identify the requested work scope.
Do not edit, create, move, rename, or delete files.
Do not use external network services or spawn additional subagents.
Do not perform the requested implementation, detailed analysis, or final review.
Avoid reading unrelated files and avoid exposing secrets or credentials.

Return a concise orientation:
1. Project purpose and current task
2. Latest confirmed issued output
3. Waiting items and next action
4. Minimum files the parent agent should inspect, with one reason per path
5. Ambiguities, competing latest-file candidates, or missing evidence

Mark filename- or timestamp-based conclusions as inferences.
"""
```

`gpt-5.6-terra`를 사용할 수 없는 환경에서는 다음 명령으로 모델을 확인하고, 빠른 읽기·탐색용 모델로 `model` 값만 교체한다.

```text
codex debug models
```

### `config.toml` 병합 내용

기존 `[agents]` 표가 없으면 다음 내용을 추가한다.

```toml
[agents]
max_concurrent_threads_per_session = 6

[agents.project_scout]
description = "Use for fast read-only project orientation, SOT review, and selecting the minimum files needed for a requested task."
config_file = "./agents/project-scout.toml"
```

이미 `[agents]`가 있으면 같은 표를 중복 생성하지 않는다. 신규 설정은 `max_concurrent_threads_per_session`을 사용한다. 기존 `max_threads`는 레거시 별칭으로 계속 작동할 수 있으므로 자동으로 개인 설정을 바꾸지 말고, `[agents.project_scout]`만 충돌 없이 병합한다.

`config_file` 상대경로는 이 항목을 정의한 `config.toml`을 기준으로 해석된다. 위 예시는 `~/.codex/config.toml`에서 `~/.codex/agents/project-scout.toml`을 가리킨다.

### `project_scout`의 역할

```text
사용자 요청
  → project_scout: SOT와 최소 관련 파일을 읽기 전용으로 확인
  → 루트 에이전트: 실제 분석·수정·검증
```

`project_scout`은 파일을 수정하지 않고 다음만 반환한다.

- 프로젝트 목적과 현재 작업
- 최신 공식 발행본
- 대기 사항과 다음 행동
- 루트 에이전트가 읽을 최소 파일 목록과 선정 이유
- 최신본 후보 충돌이나 부족한 근거

단순 질문이나 한 명령으로 끝나는 작업에는 호출하지 않는다. 서브에이전트를 사용할 수 없는 환경에서는 루트 에이전트가 같은 범위를 직접 확인한다.

## 업무 시작 순서

### 새 프로젝트를 만드는 경우

1. 빈 대상 루트를 만들고 `$initialize-project-workspace로 이 폴더의 초기화 계획을 보여줘.`라고 요청한다.
2. 대상 경로, 생성 목록과 fingerprint를 확인한 뒤 별도 메시지로 승인한다. 현재 템플릿·참조 폴더 전체를 복사해 초기화하지 않는다.
3. 초기화 검증이 통과한 프로젝트 루트를 Codex 작업 폴더로 열고 프로젝트 로컬 훅을 검토·신뢰한다.
4. 최초 SOT 작성 방법을 선택한다.
   - 사람이 직접 작성: 플레이스홀더를 한 번 직접 교체한다.
   - Codex 승인형 작성: `최초 SOT 반영안을 만들어줘`라고 요청하고, 복제된 반영안의 diff를 확인한 뒤 별도 메시지로 승인한다.
5. 급히 받은 파일은 먼저 `01_INBOX`에 넣는다. 사용자가 직접 정확한 목적지를 지시하거나 Codex의 분류안을 승인한 뒤 이동한다.
6. 내부 작업은 `03_WORK`, 실제 송부하거나 공식 공유한 파일은 `04_OUTPUT`에 둔다.
7. 전화·메일·메신저 원문은 `02_SOURCE/COMMUNICATION_LOG/CNN_yyyy-mm-dd_topic`에 보관한다.

플레이스홀더 SOT는 실제 공식 프로젝트 상태가 아니므로 최초 작성 시 `SOT/HISTORY`에 보관하지 않는다. 일부 항목만 수정한 상태라면 직접 작성 중인지 승인형 작성인지 먼저 확정한다.

### 기존 프로젝트를 이어가는 경우

1. 해당 프로젝트 루트를 Codex 작업 폴더로 연다.
2. 다음처럼 요청한다.

```text
이 프로젝트의 현재 상태를 파악하고 다음 작업을 이어가줘.
```

Codex는 `SOT/SourceOfTruth.md`를 먼저 읽고, 비단순 업무라면 `project_scout`으로 필요한 최소 파일을 확인한 뒤 작업한다.

### 자주 쓰는 요청

```text
오늘 소통 기록을 확인하고 결론 기록 초안을 보여줘.
```

```text
현재 증거를 기준으로 SOT 반영안을 보여줘.
```

```text
이 작업을 검토하고 실제로 바뀐 프로젝트 상태가 있는지 확인해줘.
```

SOT는 에이전트가 임의로 수정하지 않는다. 정확한 변경안을 먼저 제시하고 사람이 명시적으로 승인한 뒤에만 적용한다.

### INBOX 분류

분류안만 확인하려면 다음처럼 요청한다.

```text
01_INBOX를 확인하고 분류안을 보여줘. 아직 파일은 이동하지 마.
```

Codex가 제시한 원본·목적지·이유·해시를 확인한 뒤 `이 분류안대로 적용`이라고 승인한다. 사람이 정확한 원본과 목적지를 직접 지정한 경우 그 지시가 이동 승인 역할을 한다.

일반 기준자료는 `02_SOURCE`, 소통 원문과 첨부는 `COMMUNICATION_LOG`, 내부 초안과 계산은 `03_WORK`, 정식 회의 기록은 `05_MEETING`이 기본 목적지다.

### 회의자료와 발행본

- 회의용 초안은 `03_WORK`에 둔다.
- 회의 안건·회의록·결정·후속 조치는 `05_MEETING`에 둔다.
- 실제 송부했거나 회의에서 공식 공유한 자료는 반드시 새 `04_OUTPUT/OUTNN_yyyy-mm-dd_topic`에 둔다.
- `05_MEETING`에는 공식 파일을 중복 보관하지 않고 Markdown으로 OUTPUT 정본을 참조한다.

```md
2026-07-23 설계회의에서 사용한 공식 송부본은 다음 위치에 있다.

`04_OUTPUT/OUT03_2026-07-22_설계회의자료송부/발표자료.pptx`
```

## 프로젝트 로컬 훅 확인

`.codex/hooks.json`의 Stop 훅은 SOT보다 나중에 변경된 `WNN`, `OUTNN`, 소통 요약, 회의 Markdown을 찾아 주의를 준다. 자동으로 SOT를 수정하거나 실제 상태 변경을 판정하지 않는다.

프로젝트 로컬 훅은 신뢰된 프로젝트에서만 실행된다. 새 프로젝트를 초기화했거나 훅 파일이 바뀌면 Codex CLI에서 `/hooks`를 열어 소스와 명령을 검토한 뒤 신뢰한다. 훅 검사는 사람이 수행하는 업무 종료 점검과 SOT 승인을 대신하지 않는다.

## 선택 기능: SOT Git 이력

SOT 전용 자동 Git 커밋은 아직 활성화하지 않았다. 현재 템플릿과 기존 프로젝트가 Git 저장소가 아니기 때문이다.

자동 이력을 도입할 때는 다음 원칙을 권장한다.

- Codex 작업 중간이 아니라 작업 종료 시점에 실행한다.
- `SOT/SourceOfTruth.md`가 실제로 변경된 경우에만 커밋한다.
- 다른 작업 파일을 같은 커밋에 포함하지 않는다.
- OneDrive 프로젝트라면 프로젝트 내부 `.git`보다 OneDrive 밖의 별도 SOT 이력 저장소를 우선 검토한다.
- 자동 커밋은 SOT 승인 절차를 대신하지 않고, 승인 후 적용된 상태의 이력만 보존한다.

## 보안과 인코딩

- 모든 프로젝트 텍스트 파일은 UTF-8로 유지한다.
- `config.toml`의 API 키와 bearer token을 README나 프로젝트 파일에 복사하지 않는다.
- 가능한 경우 토큰 값 대신 `bearer_token_env_var` 또는 `env_http_headers`로 환경변수를 참조한다.
- 다른 컴퓨터로 옮길 때는 프로젝트 템플릿과 필요한 에이전트 설정만 복사하고, 개인 인증정보는 새 컴퓨터에서 별도로 설정한다.

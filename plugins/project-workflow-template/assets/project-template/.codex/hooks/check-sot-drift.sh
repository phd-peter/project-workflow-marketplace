#!/bin/zsh

emulate -L zsh
setopt PIPE_FAIL

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\b'/\\b}"
  value="${value//$'\f'/\\f}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  print -nr -- "$value"
}

emit_result() {
  local drift_detected="$1"
  local message="$2"
  local warn="$3"
  shift 3

  local -a paths=("$@")
  local json_paths='['
  local separator=''
  local path

  for path in "${paths[@]}"; do
    json_paths+="${separator}\"$(json_escape "$path")\""
    separator=','
  done
  json_paths+=']'

  local output="{\"continue\":true,\"driftDetected\":${drift_detected},\"changedPaths\":${json_paths},\"message\":\"$(json_escape "$message")\""

  if [[ "$warn" == 'true' ]]; then
    local system_message="$message"
    for path in "${paths[@]}"; do
      system_message+=$'\n- '"$path"
    done
    output+=",\"systemMessage\":\"$(json_escape "$system_message")\""
  fi

  output+='}'
  print -r -- "$output"
}

find_project_root() {
  local current="${PWD:A}"

  while true; do
    if [[ -f "$current/AGENTS.md" && -f "$current/SOT/SourceOfTruth.md" ]]; then
      print -r -- "$current"
      return 0
    fi

    if [[ "$current" == '/' ]]; then
      return 1
    fi

    current="${current:h}"
  done
}

collect_changed_candidates() {
  local candidate_root="$1"
  local name_pattern="$2"
  local candidate

  [[ -d "$candidate_root" ]] || return 0

  while IFS= read -r -d '' candidate; do
    if [[ -n "$(find "$candidate" -newer "$sot_path" -print -quit 2>/dev/null)" ]]; then
      changed_paths+=("${candidate#$project_root/}")
    fi
  done < <(
    find "$candidate_root" \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name "$name_pattern" \
      -print0 2>/dev/null
  )
}

collect_changed_files() {
  local candidate_root="$1"
  local name_pattern="$2"
  local candidate

  [[ -d "$candidate_root" ]] || return 0

  while IFS= read -r -d '' candidate; do
    changed_paths+=("${candidate#$project_root/}")
  done < <(
    find "$candidate_root" \
      -type f \
      -name "$name_pattern" \
      -newer "$sot_path" \
      -print0 2>/dev/null
  )
}

project_root="$(find_project_root)"

if [[ -z "$project_root" ]]; then
  emit_result \
    false \
    'SOT와 AGENTS.md가 함께 있는 프로젝트 루트를 찾지 못했습니다.' \
    true
  exit 0
fi

sot_path="$project_root/SOT/SourceOfTruth.md"
typeset -a changed_paths=()

collect_changed_candidates \
  "$project_root/03_WORK" \
  'W[0-9][0-9]_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*'
collect_changed_candidates \
  "$project_root/03_WORKS" \
  'W[0-9][0-9]_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*'
collect_changed_candidates \
  "$project_root/04_OUTPUT" \
  'OUT[0-9][0-9]_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*'
collect_changed_files \
  "$project_root/02_SOURCE/COMMUNICATION_LOG" \
  '*_summary.md'
collect_changed_files \
  "$project_root/05_MEETING" \
  '*.md'

if (( ${#changed_paths[@]} > 0 )); then
  changed_paths=("${(@ou)changed_paths}")
  emit_result \
    true \
    'SOT 이후 변경된 작업·발행·소통 요약·회의 기록 후보가 있습니다.' \
    true \
    "${changed_paths[@]}"
else
  emit_result \
    false \
    'SOT 이후 변경된 WNN·OUTNN·소통 요약·회의 기록 후보가 없습니다.' \
    false
fi

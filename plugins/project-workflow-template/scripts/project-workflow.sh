#!/bin/zsh

emulate -L zsh
setopt ERR_EXIT PIPE_FAIL NO_UNSET

script_dir="${0:A:h}"
if command -v python3 >/dev/null 2>&1; then
  python_command=(python3)
elif command -v python >/dev/null 2>&1; then
  python_command=(python)
else
  print -u2 -- 'Python 3 is required to run the project workflow migration script.'
  exit 1
fi

exec "${python_command[@]}" "$script_dir/project_workflow.py" "$@"

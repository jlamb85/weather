#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found in PATH." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
else
  echo "Working tree clean. Nothing to commit."
  exit 0
fi

map_status() {
  case "$1" in
    A) echo "add" ;;
    M) echo "update" ;;
    D) echo "delete" ;;
    R) echo "rename" ;;
    C) echo "copy" ;;
    *) echo "update" ;;
  esac
}

build_message() {
  local max_items=6
  local count=0
  local parts=()
  local line

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local status="${line%%$'\t'*}"
    local rest="${line#*$'\t'}"
    local action
    local path
    action="$(map_status "${status:0:1}")"
    if [[ "${status:0:1}" == "R" || "${status:0:1}" == "C" ]]; then
      path="${rest#*$'\t'}"
    else
      path="$rest"
    fi
    parts+=("${action} ${path}")
    count=$((count + 1))
    if [[ $count -ge $max_items ]]; then
      break
    fi
  done < <(git diff --cached --name-status)

  if [[ ${#parts[@]} -eq 0 ]]; then
    echo "update files"
    return
  fi

  local msg
  msg="$(IFS=", "; echo "${parts[*]}")"

  local total
  total="$(git diff --cached --name-status | wc -l | tr -d ' ')"
  if [[ "$total" -gt $max_items ]]; then
    msg="${msg}, and ${total}-${max_items} more"
  fi

  echo "$msg"
}

COMMIT_MSG="$(build_message)"
echo "Commit message: ${COMMIT_MSG}"

git commit -m "$COMMIT_MSG"
git push

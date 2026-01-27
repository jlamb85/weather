#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh (GitHub CLI) not found. Install it and run 'gh auth login'." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI not authenticated. Run 'gh auth login'." >&2
  exit 1
fi

TAG="${1:-$(cat VERSION)}"
TAG="${TAG#v}"

./build.sh

if ! gh release view "v$TAG" >/dev/null 2>&1; then
  gh release create "v$TAG" --title "Release v$TAG" --notes "Automated release for v$TAG"
fi

for f in dist/*; do
  base="$(basename "$f")"
  case "$base" in
    *.py|*.json|*.md|*.txt|*.spec) continue ;;
    *source*) continue ;;
  esac
  gh release upload "v$TAG" "$f" --clobber
  echo "Uploaded $f to release v$TAG"
done

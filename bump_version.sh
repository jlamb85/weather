#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f VERSION ]]; then
  echo "VERSION file not found" >&2
  exit 1
fi

if ! [[ "$(cat VERSION)" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "VERSION must be in MAJOR.MINOR.PATCH format" >&2
  exit 1
fi

bump="${1:-patch}"
IFS='.' read -r major minor patch < VERSION

case "$bump" in
  major)
    major=$((major + 1))
    minor=0
    patch=0
    ;;
  minor)
    minor=$((minor + 1))
    patch=0
    ;;
  patch)
    patch=$((patch + 1))
    ;;
  *)
    echo "Usage: $0 [major|minor|patch]" >&2
    exit 1
    ;;
 esac

echo "${major}.${minor}.${patch}" > VERSION

echo "VERSION bumped to ${major}.${minor}.${patch}"

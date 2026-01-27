#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "config.default.json" ]]; then
  echo "Missing config.default.json. Create it from config.json first." >&2
  exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found. Activate your venv or install it." >&2
  exit 1
fi

copy_runtime_files() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  cp "config.default.json" "$target_dir/config.default.json"
  if [[ ! -f "$target_dir/config.json" ]]; then
    cp "config.default.json" "$target_dir/config.json"
  fi
}

OS_NAME="$(uname -s)"
case "$OS_NAME" in
  Darwin)
    SPEC="weather-v0.1.0-macos.spec"
    NAME_ONEFILE="weather-v0.1.0-macos"
    NAME_ONEDIR="weather-v0.1.0-macos-dir"
    ;;
  Linux)
    SPEC="weather-v0.1.0-linux-x86_64.spec"
    NAME_ONEFILE="weather-v0.1.0-linux-x86_64"
    NAME_ONEDIR="weather-v0.1.0-linux-x86_64-dir"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    SPEC="weather-v0.1.0-win.exe.spec"
    NAME_ONEFILE="weather-v0.1.0-win.exe"
    NAME_ONEDIR="weather-v0.1.0-win-dir"
    ;;
  *)
    echo "Unsupported OS: $OS_NAME" >&2
    exit 1
    ;;
esac

if [[ ! -f "$SPEC" ]]; then
  echo "Missing spec file: $SPEC" >&2
  exit 1
fi

echo "Building one-file executable using $SPEC..."
pyinstaller --clean --noconfirm "$SPEC"

if [[ -f "dist/$NAME_ONEFILE" ]]; then
  copy_runtime_files "dist"
elif [[ -f "dist/$NAME_ONEFILE.exe" ]]; then
  copy_runtime_files "dist"
fi

echo "Building one-folder executable..."
pyinstaller --clean --noconfirm --onedir weather.py -n "$NAME_ONEDIR"
copy_runtime_files "dist/$NAME_ONEDIR"

echo "Builds complete. Outputs are in dist/."

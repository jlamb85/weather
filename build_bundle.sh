#!/bin/bash
# Build standalone executables for common OSs (Linux, macOS, Windows, Raspberry Pi 3/4/5)
# Usage: ./build_bundle.sh [TAG]
# Requires: pyinstaller

set -e

APP=weather.py
NAME=weather
TAG=${1:-$(cat VERSION)}
TAG=${TAG#v}

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist build ${NAME}.spec

if [[ -f "requirements.txt" ]]; then
  echo "Installing Python dependencies..."
  python -m pip install -r requirements.txt
fi

# Linux x86_64
echo "Building for Linux x86_64..."
pyinstaller --onefile --name ${NAME}-v${TAG}-linux-x86_64 $APP

# Linux arm64 (requires running on arm64 host)
echo "Building for Linux arm64..."
pyinstaller --onefile --name ${NAME}-v${TAG}-linux-arm64 $APP

# macOS (universal)
echo "Building for macOS universal..."
pyinstaller --onefile --name ${NAME}-v${TAG}-macos $APP

# Windows (x86_64)
echo "Building for Windows x86_64..."
pyinstaller --onefile --name ${NAME}-v${TAG}-win.exe $APP

# Raspberry Pi 3/4/5 (armv7/arm64)
echo "Building for Raspberry Pi (armv7)..."
pyinstaller --onefile --name ${NAME}-v${TAG}-rpi-armv7 $APP
# For arm64 (Pi 4/5 64-bit OS)
echo "Building for Raspberry Pi (arm64)..."
pyinstaller --onefile --name ${NAME}-v${TAG}-rpi-armv64 $APP

echo "All builds complete. See dist/ for output binaries."


# Changelog

## [Unreleased]

## 2026-01-28
- Searches cache now appends entries automatically on each weather lookup.
- Added searched timestamp per cache entry and daily cache reset with notice.
- Removed unused `--searches` CLI option; help now uses argparse defaults.
- Normalized app directory paths for cleaner output.
- Added `git_commit_push.sh` helper with optional editor flag.
- Added `release_version.sh` helper requiring explicit bump argument.
- Added VS Code workspace setting to open `searches` as plain text.
- Added urllib3 v2 + LibreSSL warning and pin guidance.
- Added `--version` CLI flag.

## 2026-01-26
- Added support for `-wf` as a shorthand for `--weather-favorites`.
- Documented `-wf` in help/usage text and README.
- Wind speed now displays in both knots and mph when using Fahrenheit/imperial units.
- Improved forecast table alignment, especially for emoji and short weather words.
- Output now displays the weather data source/provider.
- Configurable weather provider and unit via `config.json`.
- Multiple weather data sources supported in config.
- Robust argument parsing and error handling.
- Dependency checks for `requests` and `wcwidth`.
- 7-day (or custom N-day) forecast with table output.
- ICAO and IATA code support for airport lookup.
- Batch weather for all favorites.
- Debug output and output file support.

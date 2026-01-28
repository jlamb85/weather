# Weather CLI

A command-line tool to get current weather and multi-day forecasts by airport code (ICAO/IATA).

## Features
- Get current weather for any supported airport by ICAO or IATA code
- 7-day (or custom N-day) forecast with `--forecast`/`-f` and `--days N`
- Table output with emoji and aligned columns
- Current conditions include humidity, dew point, apparent temperature, wind gusts, pressure, cloud cover, precipitation, visibility, and UV index
- `--no-emoji` disables emoji in output if your terminal font doesn’t align them well
- List, add, and remove favorite airports
- Batch weather for all favorites with `--weather-favorites` or `-wf`
- Add custom airports to your local database
- Live update of airports.json from OurAirports
- Search airports by code, name, or city
- Configurable temperature unit (C/F) via `config.json` or `--unit`
- Wind speed in knots and mph (if using Fahrenheit)
- Debug output with `--debug`
- All output is also written to `weather_output.txt` if debug is enabled
- Request timeout protection (default: 10 seconds)
- Supports multiple weather data providers (configurable; Open-Meteo is used for live data today)
- Searches cache is reset on the first run of each day, with a notice printed when it resets

## Usage
```
./weather.py <AIRPORT_CODE> [--forecast|-f] [--days N] [--unit C|F] [--debug]
    Show weather for a specific airport (e.g. JFK, LAX)

./weather.py --weather-favorites|-wf [--forecast|-f] [--days N] [--unit C|F] [--debug]
    Show weather for all favorite airports

./weather.py --add-favorite|-af <CODE>
    Add an airport code to your favorites

./weather.py --remove-favorite|-rf <CODE>
    Remove an airport code from your favorites

./weather.py --list-favorites|-lf
    List your favorite airports

./weather.py --list-airports|-l
    List all available airport codes

./weather.py --search|-s <query>
    Search for airports by code, name, or city

./weather.py --add-airport|-a
    Add a custom airport to airports.json

./weather.py --update-airports
    Update airports.json with current global airport data

./weather.py --no-emoji
    Disable emoji in weather output

./weather.py --zone-forecast|-zf
    Show NWS zone forecast for location

./weather.py --setup
    Create a default config.json next to the executable

./weather.py --help|-h
    Show help message
```

## Configuration
- Edit `config.json` to set default temperature unit, provider, and API keys.
- Supports multiple weather providers (see config.json for details); currently Open-Meteo is used for live requests.
- Use `--setup` to create a default `config.json` if one does not exist.
## Runtime files
- The app reads and writes `config.json`, `favorites.json`, `airports.json`, `weather_output.txt`, and `searches` from the same folder as the executable.
- In development (running `python weather.py`), those files live next to `weather.py`.
- In packaged builds (PyInstaller one-file or one-folder), place the JSON files beside the built executable to edit them.
- `--setup` creates a default `config.json` automatically (no template file required).
- VS Code opens `searches` as plain text via workspace settings to avoid Python linter errors.

## airports.json fields
- `name`, `city`, `lat`, `lon`
- `icao_code`, `iata_code`
- `iso_country`, `iso_region`
- `elevation_ft`, `type`, `scheduled_service`
- `local_code`, `gps_code`, `faa_lid`

## Builds
- Use `./build.sh` to build one-file and one-folder executables for your current OS.
- The script copies `config.json` into the `dist/` output as a starting point.

## Releases
- Use `./release.sh` to create a GitHub Release and upload binary assets only.
- Source-code releases are disabled.
- Use `./bump_version.sh [major|minor|patch]` to increment `VERSION` before a release.
- Use `./bump_version.sh --set X.Y.Z` to set a specific version.
- Run `./bump_version.sh --help` to see usage.
- `VERSION` may include a leading `v` (e.g., `v0.1.0`).
### GitHub Actions release (multi-OS)
GitHub Actions builds macOS, Windows, and Linux binaries on tag pushes. To trigger a release:

```
./release_version.sh patch
```

Or manually:
```
./bump_version.sh patch
git add VERSION
git commit -m "Bump version"
git tag "$(cat VERSION)"
git push && git push --tags
```

This will publish a single release with the three binaries.

### Common GitHub CLI commands
```
# List releases
gh release list

# View a release (including assets)
gh release view v0.1.3

# Edit release title or publish a draft
gh release edit v0.1.3 --title "v0.1.3"
gh release edit v0.1.3 --draft=false

# Delete a release
gh release delete v0.1.2 -y

# Re-run a failed workflow run
gh run list -L 5
gh run rerun <run_id>

# View failed logs for a run
gh run view <run_id> --log-failed
```

## Dependencies
- Python 3
- requests
- wcwidth

Install dependencies:
```
pip install requests wcwidth
```

## Notes
- Temperature unit can be set in `config.json` ("unit": "C" or "F") or overridden with `--unit`.
- Use `--debug` to enable debug output for troubleshooting.
- `-wf` is a shorthand for `--weather-favorites`.
- `-af` is a shorthand for `--add-favorite`.
- `-rf` is a shorthand for `--remove-favorite`.
- `-lf` is a shorthand for `--list-favorites`.
- Run `--setup` once on a fresh install to create `config.json` beside the executable.
- For best alignment with emoji output, use a monospace font with good emoji rendering (e.g., SF Mono, Menlo, or Noto Sans Mono). If alignment looks off, use `--no-emoji`.
- If you're using a virtualenv, activate it before running the CLI (e.g. `source .venv/bin/activate`).

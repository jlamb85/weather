# Weather CLI

A command-line tool to get current weather and multi-day forecasts by airport code (ICAO/IATA).

## Features
- Get current weather for any supported airport by ICAO or IATA code
- 7-day (or custom N-day) forecast with `--forecast`/`-f` and `--days N`
- Table output with emoji and aligned columns
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

## Usage
```
./weather.py <AIRPORT_CODE> [--forecast|-f] [--days N] [--unit C|F] [--debug]
    Show weather for a specific airport (e.g. JFK, LAX)

./weather.py --weather-favorites [--forecast|-f] [--days N] [--unit C|F] [--debug]
./weather.py -wf [--forecast|-f] [--days N] [--unit C|F] [--debug]
    Show weather for all favorite airports

./weather.py --add-favorite <CODE>
./weather.py -af <CODE>
    Add an airport code to your favorites

./weather.py --remove-favorite <CODE>
./weather.py -rf <CODE>
    Remove an airport code from your favorites

./weather.py --list-favorites
./weather.py -lf
    List your favorite airports

./weather.py --list-airports, -l
    List all available airport codes

./weather.py --search <query>, -s <query>
    Search for airports by code, name, or city

./weather.py --add-airport, -a
    Add a custom airport to airports.json

./weather.py --update-airports
    Update airports.json with current global airport data

./weather.py --setup
    Create a default config.json next to the executable

./weather.py --help, -h
    Show help message
```

## Configuration
- Edit `config.json` to set default temperature unit, provider, and API keys.
- Supports multiple weather providers (see config.json for details); currently Open-Meteo is used for live requests.
- Use `--setup` to create a default `config.json` if one does not exist.
- `--setup` copies from `config.default.json`, which ships alongside the executable (not embedded).
## Runtime files
- The app reads and writes `config.json`, `favorites.json`, `airports.json`, and `weather_output.txt` from the same folder as the executable.
- In development (running `python weather.py`), those files live next to `weather.py`.
- In packaged builds (PyInstaller one-file or one-folder), place the JSON files beside the built executable to edit them.
- `config.default.json` is shipped alongside the executable as a template for `--setup`.

## Builds
- Use `./build.sh` to build one-file and one-folder executables for your current OS.
- The script copies `config.default.json` into the `dist/` output as `config.json`.

## Releases
- Use `./release.sh` to create a GitHub Release and upload binary assets only.
- Source-code releases are disabled.
- Use `./bump_version.sh [major|minor|patch]` to increment `VERSION` before a release.

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
- If you're using a virtualenv, activate it before running the CLI (e.g. `source .venv/bin/activate`).

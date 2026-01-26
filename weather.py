#!/usr/bin/env python3
"""
Weather CLI
-----------
Get current weather and multi-day forecasts by airport code (ICAO/IATA).

Features:
- Get current weather for any supported airport by ICAO or IATA code
- 7-day (or custom N-day) forecast with --forecast and --days N
- Table output with headers for forecast data
- List, add, and remove favorite airports
- Batch weather for all favorites with --weather-favorites
- Add custom airports to your local database
- Live update of airports.json from OurAirports
- Search airports by code, name, or city
- Configurable temperature unit (C/F) via config.json or --unit
- Debug output with --debug
- All output is also written to weather_output.txt

Dependencies:
    - requests
    - wcwidth

Usage:
  ./weather.py <AIRPORT_CODE> [--forecast|-f] [--days N] [--unit C|F] [--debug]
      Show weather for a specific airport (e.g. JFK, LAX)

  ./weather.py --weather-favorites [--forecast|-f] [--days N] [--unit C|F] [--debug]
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

  ./weather.py --help, -h
      Show help message
"""
import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Missing required module: requests. Please install it with 'pip install requests'.")
    sys.exit(1)
try:
    from wcwidth import wcswidth
except ImportError:
    print("Missing required module: wcwidth. Please install it with 'pip install wcwidth'.")
    sys.exit(1)


# Config file support for default unit
def get_config_path():
    return os.path.join(os.path.dirname(__file__), 'config.json')


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
    return {}


# Utility to write output to both console and a file

class Tee:
    def __init__(self, filename):
        self.file = open(filename, 'w')
        self.stdout = sys.stdout
        sys.stdout = self

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()

    def close(self):
        sys.stdout = self.stdout
        self.file.close()


DEBUG = False
REQUEST_TIMEOUT = 10


# Fetch weather for all favorites
def weather_for_favorites(show_forecast=False, debug=False, days=7, temp_unit_override=None):
    favorites = load_favorites()
    airports = load_airports()
    if not favorites:
        print("No favorites set.")
        return
    if debug:
        print(f"DEBUG: Running weather_for_favorites with: {sorted(favorites)}")
    # CLI override
    for code in sorted(favorites):
        if debug:
            print(f"DEBUG: Processing favorite {code}")
        if code in airports:
            get_weather_by_airport(
                code,
                show_forecast=show_forecast,
                debug=debug,
                days=days,
                temp_unit_override=temp_unit_override,
                airports=airports,
            )
        else:
            print(f"{code}: (not found in airports.json)")

# Load airports from airports.json in the project directory
def get_airports_path():
    return os.path.join(os.path.dirname(__file__), 'airports.json')


def load_airports():
    path = get_airports_path()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            airports = {}
            for code, entry in data.items():
                airports[code.upper()] = (
                    entry.get('name', ''),
                    entry.get('city', ''),
                    float(entry.get('lat', 0)),
                    float(entry.get('lon', 0)),
                )
            return airports
        except Exception as e:
            print(f"Warning: Could not load airports.json: {e}")
    print("No airports.json found or failed to load. No airports available.")
    return {}


def save_airports(airports):
    path = get_airports_path()
    data = {}
    for code, value in airports.items():
        name, city, lat, lon = value
        data[code.upper()] = {
            'name': name,
            'city': city,
            'lat': lat,
            'lon': lon
        }
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def weather_code_to_emoji(code):
    # Open-Meteo weather codes: https://open-meteo.com/en/docs#api_form
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "❓ Unknown"
    if code == 0:
        return "☀️ Clear"
    elif code in (1, 2, 3):
        return "⛅ Partly Cloudy"
    elif code in (45, 48):
        return "🌫️ Fog"
    elif code in (51, 53, 55, 56, 57):
        return "🌦️ Drizzle"
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️ Rain"
    elif code in (71, 73, 75, 77, 85, 86):
        return "❄️ Snow"
    elif code in (95, 96, 99):
        return "⛈️ Thunderstorm"
    return "❓ Unknown"


def get_weather_by_airport(
    airport_code,
    show_forecast=False,
    debug=False,
    days=7,
    temp_unit_override=None,
    airports=None,
):
    if debug:
        print(f"DEBUG: get_weather_by_airport({airport_code}, show_forecast={show_forecast}, days={days})")
    airports = airports or load_airports()
    airport = airports.get(airport_code.upper())
    if not airport:
        print(f"Unknown airport code: {airport_code}")
        return
    # Determine temperature unit from config
    config = load_config()
    temp_unit = (temp_unit_override or config.get('unit', 'C')).upper()
    temp_param = 'fahrenheit' if temp_unit == 'F' else 'celsius'
    temp_symbol = '°F' if temp_unit == 'F' else '°C'
    provider = config.get('provider', 'open-meteo')
    providers = config.get('providers', {})
    provider_info = providers.get(provider, {})
    provider_url = provider_info.get('url', 'https://api.open-meteo.com/v1/forecast')
    name, city, lat, lon = airport
    # For now, only open-meteo is implemented for live data
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current_weather=true&temperature_unit={temp_param}&windspeed_unit=kn"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,sunrise,sunset&forecast_days={days}&timezone=auto"
    )
    if debug:
        print(f"DEBUG: Requesting URL: {url}")
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if debug:
            print(f"DEBUG: HTTP status: {resp.status_code}")
        try:
            data = resp.json()
            if debug:
                print(f"DEBUG: Response JSON: {json.dumps(data, indent=2)[:1000]}")
        except Exception as e:
            if debug:
                print(f"DEBUG: Failed to parse JSON: {e}")
            data = {}
    except requests.RequestException as e:
        print(f"Error: Could not fetch weather for {airport_code}: {e}")
        return

    if resp.status_code != 200:
        print(f"Error: Could not fetch weather for {airport_code} (status {resp.status_code})")
        return
    name, city, lat, lon = airport
    current = data.get("current_weather", {})
    print("\n" + "=" * 40)
    print(f"Weather for {airport_code.upper()} - {name} ({city})")
    print(f"Location: lat {lat:.4f}, lon {lon:.4f}")
    print(f"Source: {provider} ({provider_url})")
    print("=" * 40)
    daily = data.get('daily', {})
    # Show today's sunrise/sunset if available
    today_idx = 0
    sunrise = None
    sunset = None
    if 'sunrise' in daily and 'sunset' in daily and 'time' in daily:
        from datetime import datetime
        now = datetime.now().date()
        for i, d in enumerate(daily['time']):
            if d == str(now):
                today_idx = i
                break
        try:
            sunrise = daily['sunrise'][today_idx]
            sunset = daily['sunset'][today_idx]
        except Exception:
            pass
    if current:
        print(f"Current:  {weather_code_to_emoji(current.get('weathercode', -1))}")
        print(f"  Temp:    {current.get('temperature', 'N/A')}{temp_symbol}")
        wind_dir = current.get('winddirection', 'N/A')
        wind_speed_kt = current.get('windspeed', 'N/A')
        wind_speed_str = f"{wind_speed_kt} kt"
        # Convert knots to mph if temp_unit is F (imperial)
        try:
            wind_speed_val = float(wind_speed_kt)
            wind_speed_mph = wind_speed_val * 1.15078
            wind_speed_mph_str = f"{wind_speed_mph:.1f} mph"
        except Exception:
            wind_speed_mph_str = None
        if temp_unit == 'F' and wind_speed_mph_str:
            wind_speed_str += f" / {wind_speed_mph_str}"
        print(f"  Wind:    {wind_dir}° at {wind_speed_str}")
        print(f"  Time:    {current.get('time', 'N/A')}")
        if sunrise and sunset:
            print(f"  Sunrise: {sunrise}  Sunset: {sunset}")
    else:
        print("No current weather data available.")

    if show_forecast:
        forecast_days = daily.get('time', [])
        tmax = daily.get('temperature_2m_max', [])
        tmin = daily.get('temperature_2m_min', [])
        wcode = daily.get('weathercode', [])
        precip = daily.get('precipitation_sum', [])
        sunrises = daily.get('sunrise', [])
        sunsets = daily.get('sunset', [])
        print(f"\n{min(days, len(forecast_days))}-Day Forecast:")
        print("-" * 80)
        # Calculate max display width for all columns for perfect alignment
        weather_strs = []
        date_strs = []
        tmax_strs = []
        tmin_strs = []
        precip_strs = []
        sunrise_strs = []
        sunset_strs = []
        pad_weather = 22
        pad_date = 12
        pad_temp = 8
        pad_precip = 8
        pad_sun = 8
        n = min(days, len(forecast_days))
        for i in range(n):
            weather_str = weather_code_to_emoji(wcode[i])
            parts = weather_str.split()
            if len(parts) > 1:
                icon = parts[0]
                desc = ' '.join(parts[1:])
                weather_str = f"{icon} {desc}"
            elif len(parts) == 1:
                # For single-word, split emoji from word using unicode category
                import unicodedata
                s = parts[0]
                # Find the first non-symbol character (start of word)
                split_idx = 0
                for idx, ch in enumerate(s):
                    if unicodedata.category(ch)[0] != 'S':
                        split_idx = idx
                        break
                # Emoji is up to split_idx, word is after
                icon = s[:split_idx]
                desc = s[split_idx:]
                if not icon:
                    # fallback: treat as no emoji
                    weather_str = desc
                else:
                    weather_str = f"{icon} {desc}"
            weather_strs.append(weather_str)
            date_strs.append(str(forecast_days[i]))
            tmax_strs.append(f"{tmax[i]}{temp_symbol}")
            tmin_strs.append(f"{tmin[i]}{temp_symbol}")
            precip_strs.append(f"{precip[i]}mm")
            sr = sunrises[i][-5:] if i < len(sunrises) and sunrises[i] else ''
            ss = sunsets[i][-5:] if i < len(sunsets) and sunsets[i] else ''
            sunrise_strs.append(sr)
            sunset_strs.append(ss)
        # Find max display width for each column (Weather uses wcswidth for display width)
        max_weather_width = max([wcswidth(ws) for ws in weather_strs] + [pad_weather])
        max_date_width = max([wcswidth(ds) for ds in date_strs] + [pad_date])
        max_tmax_width = max([wcswidth(ts) for ts in tmax_strs] + [pad_temp])
        max_tmin_width = max([wcswidth(ts) for ts in tmin_strs] + [pad_temp])
        max_precip_width = max([wcswidth(ps) for ps in precip_strs] + [pad_precip])
        max_sunrise_width = max([wcswidth(s) for s in sunrise_strs] + [pad_sun])
        max_sunset_width = max([wcswidth(s) for s in sunset_strs] + [pad_sun])
        # Print header
        print(
            f"{'Date':<{max_date_width}} {'Weather':<{max_weather_width}} {'High':>{max_tmax_width}} {'Low':>{max_tmin_width}} {'Precip':>{max_precip_width}} {'Sunrise':>{max_sunrise_width}} {'Sunset':>{max_sunset_width}}")
        print("-" * (
                    max_date_width + max_weather_width + max_tmax_width + max_tmin_width + max_precip_width + max_sunrise_width + max_sunset_width + 6))
        # Print rows
        for i in range(n):
            ws = weather_strs[i]
            ds = date_strs[i]
            tmaxs = tmax_strs[i]
            tmins = tmin_strs[i]
            precs = precip_strs[i]
            srs = sunrise_strs[i]
            sss = sunset_strs[i]
            # Pad/truncate Weather column using wcswidth, left-align (revert)
            ws_disp = wcswidth(ws)
            if ws_disp < max_weather_width:
                ws = ws + ' ' * (max_weather_width - ws_disp)
            elif ws_disp > max_weather_width:
                parts = ws.split()
                if len(parts) > 1:
                    icon = parts[0]
                    desc = ' '.join(parts[1:])
                    max_desc = max(1, max_weather_width - wcswidth(icon) - 1)
                    desc = desc[:max_desc]
                    ws = f"{icon} {desc}"
                    ws_disp = wcswidth(ws)
                    if ws_disp < max_weather_width:
                        ws = ws + ' ' * (max_weather_width - ws_disp)
                else:
                    ws = ws[:max_weather_width]
            ds_disp = wcswidth(ds)
            if ds_disp < max_date_width:
                ds = ds + ' ' * (max_date_width - ds_disp)
            tmax_disp = wcswidth(tmaxs)
            if tmax_disp < max_tmax_width:
                tmaxs = ' ' * (max_tmax_width - tmax_disp) + tmaxs
            tmin_disp = wcswidth(tmins)
            if tmin_disp < max_tmin_width:
                tmins = ' ' * (max_tmin_width - tmin_disp) + tmins
            prec_disp = wcswidth(precs)
            if prec_disp < max_precip_width:
                precs = ' ' * (max_precip_width - prec_disp) + precs
            srs_disp = wcswidth(srs)
            if srs_disp < max_sunrise_width:
                srs = ' ' * (max_sunrise_width - srs_disp) + srs
            sss_disp = wcswidth(sss)
            if sss_disp < max_sunset_width:
                sss = ' ' * (max_sunset_width - sss_disp) + sss
            print(f"{ds} {ws} {tmaxs} {tmins} {precs} {srs} {sss}")
    print("=" * 40 + "\n")


def add_custom_airport():
    print("Add a custom airport:")
    code = input("Airport code (3-4 letters): ").strip().upper()
    name = input("Airport name: ").strip()
    city = input("City: ").strip()
    lat = input("Latitude: ").strip()
    lon = input("Longitude: ").strip()
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        print("Invalid latitude or longitude.")
        return
    # Add to airports.json
    airports = load_airports()
    airports[code] = (name, city, lat, lon)
    save_airports(airports)
    print(f"Added custom airport {code}: {name} ({city})")


def load_favorites():
    # Stub: load favorites from favorites.json
    path = os.path.join(os.path.dirname(__file__), 'favorites.json')
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load favorites.json: {e}")
    return []


def add_favorite(code):
    # Stub: add a favorite airport code
    favorites = load_favorites()
    code = code.upper()
    if code not in favorites:
        favorites.append(code)
        path = os.path.join(os.path.dirname(__file__), 'favorites.json')
        with open(path, 'w') as f:
            json.dump(favorites, f, indent=2)
        print(f"Added {code} to favorites.")
    else:
        print(f"{code} is already a favorite.")


def remove_favorite(code):
    # Stub: remove a favorite airport code
    favorites = load_favorites()
    code = code.upper()
    if code in favorites:
        favorites.remove(code)
        path = os.path.join(os.path.dirname(__file__), 'favorites.json')
        with open(path, 'w') as f:
            json.dump(favorites, f, indent=2)
        print(f"Removed {code} from favorites.")
    else:
        print(f"{code} is not in favorites.")


def list_favorites():
    # Stub: list favorite airport codes
    favorites = load_favorites()
    if not favorites:
        print("No favorites set.")
    else:
        print("Favorite airports:")
        for code in favorites:
            print(f"  {code}")


def update_airports():
    """
    Download and update airports.json from OurAirports open data.
    Only includes airports with valid ICAO or IATA code, name, city, lat, lon.
    """
    import csv
    import urllib.request
    url = "https://davidmegginson.github.io/ourairports-data/airports.csv"
    print("Downloading airports.csv from OurAirports...")
    try:
        response = urllib.request.urlopen(url)
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.DictReader(lines)
        airports = {}
        for row in reader:
            icao = row.get('icao_code', '').upper()
            iata = row.get('iata_code', '').upper()
            name = row.get('name', '').strip()
            city = row.get('municipality', '').strip()
            lat = row.get('latitude_deg')
            lon = row.get('longitude_deg')
            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue
            if not name or not city:
                continue
            # Always add both ICAO and IATA codes as separate keys if both exist
            if icao:
                airports[icao] = (name, city, lat, lon)
            if iata and iata != icao:
                airports[iata] = (name, city, lat, lon)
        save_airports(airports)
        print(f"Updated airports.json with {len(airports)} airports.")
    except Exception as e:
        print(f"Failed to update airports: {e}")


def list_airports():
    # Stub: list all airports
    airports = load_airports()
    if not airports:
        print("No airports available.")
    else:
        print("Available airports:")
        for code, (name, city, lat, lon) in sorted(airports.items()):
            print(f"  {code}: {name} ({city})")


def search_airports(query):
    # Stub: search airports by code, name, or city
    airports = load_airports()
    query = query.lower()
    found = False
    for code, (name, city, lat, lon) in airports.items():
        if query in code.lower() or query in name.lower() or query in city.lower():
            print(f"  {code}: {name} ({city})")
            found = True
    if not found:
        print("No airports found matching query.")


def main():
    parser = argparse.ArgumentParser(
        description="Get current weather by airport code (ICAO/IATA).",
        add_help=False,
    )
    parser.add_argument("airport_code", nargs="?", help="Airport code (e.g. JFK, LAX)")
    parser.add_argument("--forecast", "-f", action="store_true", help="Show multi-day forecast")
    parser.add_argument("--days", type=int, default=7, help="Number of forecast days (1-16)")
    parser.add_argument("--unit", choices=["C", "F", "c", "f"], help="Temperature unit")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--weather-favorites", "-wf", action="store_true", help="Weather for favorites")
    parser.add_argument("--add-favorite", "-af", metavar="CODE", help="Add favorite airport code")
    parser.add_argument("--remove-favorite", "-rf", metavar="CODE", help="Remove favorite airport code")
    parser.add_argument("--list-favorites", "-lf", action="store_true", help="List favorite airports")
    parser.add_argument("--list-airports", "-l", action="store_true", help="List all airports")
    parser.add_argument("--search", "-s", metavar="QUERY", help="Search airports")
    parser.add_argument("--add-airport", "-a", action="store_true", help="Add a custom airport")
    parser.add_argument("--update-airports", action="store_true", help="Update airports database")
    parser.add_argument("--help", "-h", action="store_true", help="Show help message")

    args = parser.parse_args()

    if args.help or len(sys.argv) < 2:
        print("""
weather.py: Get current weather by airport code (ICAO/IATA)

Usage:
  ./weather.py <AIRPORT_CODE> [--forecast|-f] [--days N] [--unit C|F] [--debug]
      Show weather for a specific airport (code: e.g. JFK, LAX)
      --forecast, -f   Show multi-day forecast
      --days N         Number of days for forecast (default: 7, max: 16)
      --unit C|F       Celsius or Fahrenheit (overrides config.json)
      --debug          Show debug output

  ./weather.py --weather-favorites [--forecast|-f] [--days N] [--unit C|F] [--debug]
  ./weather.py -wf [--forecast|-f] [--days N] [--unit C|F] [--debug]
      Show weather for all favorite airports
      --forecast, -f   Show multi-day forecast
      --days N         Number of days for forecast (default: 7, max: 16)
      --unit C|F       Celsius or Fahrenheit (overrides config.json)
      --debug          Show debug output

  ./weather.py --add-favorite <CODE>
      Add an airport code to your favorites

  ./weather.py --remove-favorite <CODE>
      Remove an airport code from your favorites

  ./weather.py --list-favorites
      List your favorite airports

  ./weather.py --list-airports, -l
      List all available airport codes

  ./weather.py --search <query>, -s <query>
      Search for airports by code, name, or city

  ./weather.py --add-airport, -a
      Add a custom airport to airports.json

  ./weather.py --update-airports
      Update airports.json with current global airport data
""")
        return

    days = max(1, min(args.days, 16))
    if args.days != days:
        print(f"Note: --days clamped to {days} (supported range: 1-16).")

    temp_unit_override = args.unit.upper() if args.unit else None
    debug = args.debug
    tee = None
    try:
        if debug:
            tee = Tee(os.path.join(os.path.dirname(__file__), "weather_output.txt"))

        if args.weather_favorites:
            weather_for_favorites(
                show_forecast=args.forecast,
                debug=debug,
                days=days,
                temp_unit_override=temp_unit_override,
            )
            return
        if args.add_favorite:
            add_favorite(args.add_favorite)
            return
        if args.remove_favorite:
            remove_favorite(args.remove_favorite)
            return
        if args.list_favorites:
            list_favorites()
            return
        if args.update_airports:
            update_airports()
            return
        if args.list_airports:
            list_airports()
            return
        if args.search:
            search_airports(args.search)
            return
        if args.add_airport:
            add_custom_airport()
            return
        if args.airport_code:
            get_weather_by_airport(
                args.airport_code,
                show_forecast=args.forecast,
                debug=debug,
                days=days,
                temp_unit_override=temp_unit_override,
            )
            return

        print("No command provided. Use --help for usage.")
    finally:
        if tee is not None:
            tee.close()


if __name__ == "__main__":
    main()

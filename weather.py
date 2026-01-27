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
    import certifi
except ImportError:
    certifi = None
try:
    from wcwidth import wcswidth
except ImportError:
    print("Missing required module: wcwidth. Please install it with 'pip install wcwidth'.")
    sys.exit(1)


# Config file support for default unit
def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def get_config_path():
    return os.path.join(get_app_dir(), 'config.json')


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
    return {}


def setup_default_config():
    path = get_config_path()
    if os.path.exists(path):
        print(f"config.json already exists at {path}")
        return
    try:
        data = {
            "unit": "F",
            "provider": "noaa",
            "providers": {
                "open-meteo": {
                    "url": "https://api.open-meteo.com/v1/forecast",
                    "notes": "Free, no API key required, global",
                },
                "noaa": {
                    "url": "https://api.weather.gov/",
                    "notes": "US only, no API key required, official NWS",
                },
                "openweathermap": {
                    "url": "https://api.openweathermap.org/data/2.5/onecall",
                    "notes": "Free tier, global, requires API key (https://openweathermap.org/api)",
                    "api_key": "YOUR_OPENWEATHERMAP_API_KEY",
                },
                "weatherapi": {
                    "url": "https://api.weatherapi.com/v1/forecast.json",
                    "notes": "Free tier, global, requires API key (https://www.weatherapi.com/)",
                    "api_key": "YOUR_WEATHERAPI_KEY",
                },
                "weatherbit": {
                    "url": "https://api.weatherbit.io/v2.0/forecast/daily",
                    "notes": "Free tier, global, requires API key (https://www.weatherbit.io/api)",
                    "api_key": "YOUR_WEATHERBIT_KEY",
                },
                "visualcrossing": {
                    "url": "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline",
                    "notes": "Free tier, global, requires API key (https://www.visualcrossing.com/weather-api)",
                    "api_key": "YOUR_VISUALCROSSING_KEY",
                },
            },
        }
        with open(path, "w") as dst:
            json.dump(data, dst, indent=2)
        print(f"Created default config.json at {path}")
    except Exception as e:
        print(f"Error: Could not create config.json: {e}")


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
def weather_for_favorites(show_forecast=False, debug=False, days=7, temp_unit_override=None, no_emoji=False):
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
                no_emoji=no_emoji,
            )
        else:
            print(f"{code}: (not found in airports.json)")

# Load airports from airports.json in the project directory
def get_airports_path():
    return os.path.join(get_app_dir(), 'airports.json')


def load_airports():
    path = get_airports_path()
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            airports = {}
            for code, entry in data.items():
                code_upper = code.upper()
                if isinstance(entry, dict):
                    airports[code_upper] = {
                        "name": entry.get("name", ""),
                        "city": entry.get("city", ""),
                        "lat": float(entry.get("lat", 0)),
                        "lon": float(entry.get("lon", 0)),
                        "icao_code": entry.get("icao_code", ""),
                        "iata_code": entry.get("iata_code", ""),
                        "iso_country": entry.get("iso_country", ""),
                        "iso_region": entry.get("iso_region", ""),
                        "elevation_ft": entry.get("elevation_ft"),
                        "type": entry.get("type", ""),
                        "scheduled_service": entry.get("scheduled_service", ""),
                        "local_code": entry.get("local_code", ""),
                        "gps_code": entry.get("gps_code", ""),
                        "faa_lid": entry.get("faa_lid", entry.get("local_code", "")),
                    }
                elif isinstance(entry, (list, tuple)) and len(entry) >= 4:
                    airports[code_upper] = {
                        "name": entry[0],
                        "city": entry[1],
                        "lat": float(entry[2]),
                        "lon": float(entry[3]),
                        "icao_code": "",
                        "iata_code": "",
                        "iso_country": "",
                        "iso_region": "",
                        "elevation_ft": None,
                        "type": "",
                        "scheduled_service": "",
                        "local_code": "",
                        "gps_code": "",
                        "faa_lid": "",
                    }
            return airports
        except Exception as e:
            print(f"Warning: Could not load airports.json: {e}")
    print("No airports.json found or failed to load. No airports available.")
    return {}


def save_airports(airports):
    path = get_airports_path()
    data = {}
    for code, entry in airports.items():
        if isinstance(entry, dict):
            data[code.upper()] = {
                "name": entry.get("name", ""),
                "city": entry.get("city", ""),
                "lat": entry.get("lat", 0),
                "lon": entry.get("lon", 0),
                "icao_code": entry.get("icao_code", ""),
                "iata_code": entry.get("iata_code", ""),
                "iso_country": entry.get("iso_country", ""),
                "iso_region": entry.get("iso_region", ""),
                "elevation_ft": entry.get("elevation_ft"),
                "type": entry.get("type", ""),
                "scheduled_service": entry.get("scheduled_service", ""),
                "local_code": entry.get("local_code", ""),
                "gps_code": entry.get("gps_code", ""),
                "faa_lid": entry.get("faa_lid", entry.get("local_code", "")),
            }
        else:
            name, city, lat, lon = entry
            data[code.upper()] = {
                "name": name,
                "city": city,
                "lat": lat,
                "lon": lon,
                "icao_code": "",
                "iata_code": "",
                "iso_country": "",
                "iso_region": "",
                "elevation_ft": None,
                "type": "",
                "scheduled_service": "",
                "local_code": "",
                "gps_code": "",
                "faa_lid": "",
            }
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def weather_code_to_emoji(code, with_emoji=True):
    # Open-Meteo weather codes: https://open-meteo.com/en/docs#api_form
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "❓ Unknown" if with_emoji else "Unknown"
    if code == 0:
        return "☀️ Clear" if with_emoji else "Clear"
    elif code in (1, 2, 3):
        return "⛅ Partly Cloudy" if with_emoji else "Partly Cloudy"
    elif code in (45, 48):
        return "🌫️ Fog" if with_emoji else "Fog"
    elif code in (51, 53, 55, 56, 57):
        return "🌦️ Drizzle" if with_emoji else "Drizzle"
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️ Rain" if with_emoji else "Rain"
    elif code in (71, 73, 75, 77, 85, 86):
        return "❄️ Snow" if with_emoji else "Snow"
    elif code in (95, 96, 99):
        return "⛈️ Thunderstorm" if with_emoji else "Thunderstorm"
    return "❓ Unknown" if with_emoji else "Unknown"


def get_weather_by_airport(
    airport_code,
    show_forecast=False,
    debug=False,
    days=7,
    temp_unit_override=None,
    airports=None,
    no_emoji=False,
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
    name = airport.get("name", "")
    city = airport.get("city", "")
    lat = airport.get("lat", 0)
    lon = airport.get("lon", 0)
    # For now, only open-meteo is implemented for live data
    current_vars = ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "showers",
        "snowfall",
        "weather_code",
        "cloud_cover",
        "visibility",
        "uv_index",
        "pressure_msl",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
    ])
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current={current_vars}&temperature_unit={temp_param}&wind_speed_unit=kn"
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
    current = data.get("current", {}) or data.get("current_weather", {})
    current_units = data.get("current_units", {}) or data.get("current_weather_units", {})
    print("\n" + "=" * 40)
    print(f"Weather for {airport_code.upper()} - {name} ({city})")
    icao_code = airport.get("icao_code", "")
    iata_code = airport.get("iata_code", "")
    faa_lid = airport.get("faa_lid", "")
    codes = []
    if icao_code:
        codes.append(f"ICAO {icao_code}")
    if iata_code:
        codes.append(f"IATA {iata_code}")
    elif faa_lid:
        codes.append(f"FAA {faa_lid}")
    if codes:
        print(f"Codes: {', '.join(codes)}")
    iso_region = airport.get("iso_region", "")
    iso_country = airport.get("iso_country", "")
    if iso_region or iso_country:
        region_str = ", ".join([v for v in [iso_region, iso_country] if v])
        print(f"Region: {region_str}")
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
        weather_code = current.get("weather_code", current.get("weathercode", -1))
        print(f"Current:  {weather_code_to_emoji(weather_code, with_emoji=not no_emoji)}")
        temp_val = current.get("temperature_2m", current.get("temperature", "N/A"))
        print(f"  Temp:    {temp_val}{temp_symbol}")
        apparent = current.get("apparent_temperature", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        dew_point = current.get("dew_point_2m", "N/A")
        print(f"  Feels:   {apparent}{temp_symbol}")
        print(f"  Humid:   {humidity}{current_units.get('relative_humidity_2m', '%')}")
        print(f"  DewPt:   {dew_point}{temp_symbol}")
        wind_dir = current.get('wind_direction_10m', current.get('winddirection', 'N/A'))
        wind_speed_kt = current.get('wind_speed_10m', current.get('windspeed', 'N/A'))
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
        wind_gusts = current.get("wind_gusts_10m", "N/A")
        print(f"  Wind:    {wind_dir}° at {wind_speed_str} (gusts {wind_gusts} kt)")
        pressure_msl = current.get("pressure_msl", "N/A")
        surface_pressure = current.get("surface_pressure", "N/A")
        cloud_cover = current.get("cloud_cover", "N/A")
        visibility = current.get("visibility", "N/A")
        uv_index = current.get("uv_index", "N/A")
        precipitation = current.get("precipitation", "N/A")
        rain = current.get("rain", "N/A")
        showers = current.get("showers", "N/A")
        snowfall = current.get("snowfall", "N/A")
        print(f"  Cloud:   {cloud_cover}{current_units.get('cloud_cover', '%')}")
        print(f"  Vis:     {visibility}{current_units.get('visibility', 'm')}")
        print(f"  UV:      {uv_index}{current_units.get('uv_index', '')}")
        print(f"  Press:   {pressure_msl} {current_units.get('pressure_msl', 'hPa')} (surface {surface_pressure} {current_units.get('surface_pressure', 'hPa')})")
        print(f"  Precip:  {precipitation}{current_units.get('precipitation', 'mm')} (rain {rain}, showers {showers}, snow {snowfall})")
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
        weather_icons = []
        weather_descs = []
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
            weather_str = weather_code_to_emoji(wcode[i], with_emoji=not no_emoji)
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
            icon = ""
            desc = weather_str
            if " " in weather_str:
                icon, desc = weather_str.split(" ", 1)
            weather_icons.append(icon)
            weather_descs.append(desc)
            date_strs.append(str(forecast_days[i]))
            tmax_strs.append(f"{tmax[i]}{temp_symbol}")
            tmin_strs.append(f"{tmin[i]}{temp_symbol}")
            precip_strs.append(f"{precip[i]}mm")
            sr = sunrises[i][-5:] if i < len(sunrises) and sunrises[i] else ''
            ss = sunsets[i][-5:] if i < len(sunsets) and sunsets[i] else ''
            sunrise_strs.append(sr)
            sunset_strs.append(ss)
        def display_width(text):
            width = wcswidth(text)
            if width < 0:
                width = len(text)
            return width

        max_icon_width = 6
        max_desc_width = max([display_width(d) for d in weather_descs] + [display_width("Weather"), pad_weather])
        max_date_width = max([display_width(ds) for ds in date_strs] + [pad_date, display_width("Date")])
        max_tmax_width = max([display_width(ts) for ts in tmax_strs] + [pad_temp, display_width("High")])
        max_tmin_width = max([display_width(ts) for ts in tmin_strs] + [pad_temp, display_width("Low")])
        max_precip_width = max([display_width(ps) for ps in precip_strs] + [pad_precip, display_width("Precip")])
        max_sunrise_width = max([display_width(s) for s in sunrise_strs] + [pad_sun, display_width("Sunrise")])
        max_sunset_width = max([display_width(s) for s in sunset_strs] + [pad_sun, display_width("Sunset")])
        # Print header
        if no_emoji:
            print(
                f"{'Date':<{max_date_width}} {'Weather':<{max_desc_width}} {'High':>{max_tmax_width}} {'Low':>{max_tmin_width}} {'Precip':>{max_precip_width}} {'Sunrise':>{max_sunrise_width}} {'Sunset':>{max_sunset_width}}")
            print("-" * (
                        max_date_width + max_desc_width + max_tmax_width + max_tmin_width + max_precip_width + max_sunrise_width + max_sunset_width + 6))
        else:
            print(
                f"{'Date':<{max_date_width}} {'Wx':<{max_icon_width}} {'Weather':<{max_desc_width}} {'High':>{max_tmax_width}} {'Low':>{max_tmin_width}} {'Precip':>{max_precip_width}} {'Sunrise':>{max_sunrise_width}} {'Sunset':>{max_sunset_width}}")
            print("-" * (
                        max_date_width + max_icon_width + max_desc_width + max_tmax_width + max_tmin_width + max_precip_width + max_sunrise_width + max_sunset_width + 7))
        # Print rows
        for i in range(n):
            icon = weather_icons[i] or ""
            desc = weather_descs[i] or ""
            ds = date_strs[i]
            tmaxs = tmax_strs[i]
            tmins = tmin_strs[i]
            precs = precip_strs[i]
            srs = sunrise_strs[i]
            sss = sunset_strs[i]
            icon_disp = display_width(icon)
            if icon_disp < max_icon_width:
                icon = icon + ' ' * (max_icon_width - icon_disp)
            desc_disp = display_width(desc)
            if desc_disp < max_desc_width:
                desc = desc + ' ' * (max_desc_width - desc_disp)
            ds_disp = display_width(ds)
            if ds_disp < max_date_width:
                ds = ds + ' ' * (max_date_width - ds_disp)
            tmax_disp = display_width(tmaxs)
            if tmax_disp < max_tmax_width:
                tmaxs = ' ' * (max_tmax_width - tmax_disp) + tmaxs
            tmin_disp = display_width(tmins)
            if tmin_disp < max_tmin_width:
                tmins = ' ' * (max_tmin_width - tmin_disp) + tmins
            prec_disp = display_width(precs)
            if prec_disp < max_precip_width:
                precs = ' ' * (max_precip_width - prec_disp) + precs
            srs_disp = display_width(srs)
            if srs_disp < max_sunrise_width:
                srs = ' ' * (max_sunrise_width - srs_disp) + srs
            sss_disp = display_width(sss)
            if sss_disp < max_sunset_width:
                sss = ' ' * (max_sunset_width - sss_disp) + sss
            if no_emoji:
                print(f"{ds} {desc} {tmaxs} {tmins} {precs} {srs} {sss}")
            else:
                print(f"{ds} {icon} {desc} {tmaxs} {tmins} {precs} {srs} {sss}")
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
    airports[code] = {
        "name": name,
        "city": city,
        "lat": lat,
        "lon": lon,
        "icao_code": code if len(code) == 4 else "",
        "iata_code": code if len(code) == 3 else "",
        "iso_country": "",
        "iso_region": "",
        "elevation_ft": None,
        "type": "custom_airport",
        "scheduled_service": "",
    }
    save_airports(airports)
    print(f"Added custom airport {code}: {name} ({city})")


def load_favorites():
    # Stub: load favorites from favorites.json
    path = os.path.join(get_app_dir(), 'favorites.json')
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
        path = os.path.join(get_app_dir(), 'favorites.json')
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
        path = os.path.join(get_app_dir(), 'favorites.json')
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


def list_airports():
    # Stub: list all airports
    airports = load_airports()
    if not airports:
        print("No airports available.")
    else:
        print("Available airports:")
        for code, entry in sorted(airports.items()):
            name = entry.get("name", "")
            city = entry.get("city", "")
            iso_region = entry.get("iso_region", "")
            iso_country = entry.get("iso_country", "")
            region_str = ", ".join([v for v in [iso_region, iso_country] if v])
            suffix = f" ({city})" if city else ""
            if region_str:
                suffix = f"{suffix} [{region_str}]"
            print(f"  {code}: {name}{suffix}")


def search_airports(query):
    # Stub: search airports by code, name, or city
    airports = load_airports()
    query = query.lower()
    found = False
    for code, entry in airports.items():
        name = entry.get("name", "")
        city = entry.get("city", "")
        iso_country = entry.get("iso_country", "")
        iso_region = entry.get("iso_region", "")
        airport_type = entry.get("type", "")
        scheduled_service = entry.get("scheduled_service", "")
        local_code = entry.get("local_code", "")
        gps_code = entry.get("gps_code", "")
        faa_lid = entry.get("faa_lid", "")
        haystack = " ".join([
            code,
            name,
            city,
            iso_country,
            iso_region,
            airport_type,
            scheduled_service,
            local_code,
            gps_code,
            faa_lid,
        ]).lower()
        if query in haystack:
            region_str = ", ".join([v for v in [iso_region, iso_country] if v])
            suffix = f" ({city})" if city else ""
            if region_str:
                suffix = f"{suffix} [{region_str}]"
            print(f"  {code}: {name}{suffix}")
            found = True
    if not found:
        print("No airports found matching query.")


def update_airports():
    """
    Download and update airports.json from OurAirports open data.
    """
    import csv
    import ssl
    import urllib.request
    url = "https://davidmegginson.github.io/ourairports-data/airports.csv"
    print("Downloading airports.csv from OurAirports...")
    try:
        if certifi is not None:
            context = ssl.create_default_context(cafile=certifi.where())
            response = urllib.request.urlopen(url, context=context)
        else:
            response = urllib.request.urlopen(url)
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.DictReader(lines)
        airports = {}
        for row in reader:
            icao = row.get('icao_code', '').upper()
            iata = row.get('iata_code', '').upper()
            name = row.get('name', '').strip()
            city = row.get('municipality', '').strip()
            iso_country = row.get('iso_country', '').strip()
            iso_region = row.get('iso_region', '').strip()
            local_code = row.get('local_code', '').strip()
            gps_code = row.get('gps_code', '').strip()
            faa_lid = local_code
            elevation_ft = row.get('elevation_ft')
            airport_type = row.get('type', '').strip()
            scheduled_service = row.get('scheduled_service', '').strip()
            lat = row.get('latitude_deg')
            lon = row.get('longitude_deg')
            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue
            if not name:
                continue
            try:
                elevation_ft = int(float(elevation_ft)) if elevation_ft not in (None, "") else None
            except (TypeError, ValueError):
                elevation_ft = None
            if icao:
                airports[icao] = {
                    "name": name,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "icao_code": icao,
                    "iata_code": iata,
                    "iso_country": iso_country,
                    "iso_region": iso_region,
                    "elevation_ft": elevation_ft,
                    "type": airport_type,
                    "scheduled_service": scheduled_service,
                    "local_code": local_code,
                    "gps_code": gps_code,
                    "faa_lid": faa_lid,
                }
            if iata and iata != icao:
                airports[iata] = {
                    "name": name,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "icao_code": icao,
                    "iata_code": iata,
                    "iso_country": iso_country,
                    "iso_region": iso_region,
                    "elevation_ft": elevation_ft,
                    "type": airport_type,
                    "scheduled_service": scheduled_service,
                    "local_code": local_code,
                    "gps_code": gps_code,
                    "faa_lid": faa_lid,
                }
            if local_code and local_code not in (icao, iata):
                airports[local_code] = {
                    "name": name,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "icao_code": icao,
                    "iata_code": iata,
                    "iso_country": iso_country,
                    "iso_region": iso_region,
                    "elevation_ft": elevation_ft,
                    "type": airport_type,
                    "scheduled_service": scheduled_service,
                    "local_code": local_code,
                    "gps_code": gps_code,
                    "faa_lid": faa_lid,
                }
            if gps_code and gps_code not in (icao, iata, local_code):
                airports[gps_code] = {
                    "name": name,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "icao_code": icao,
                    "iata_code": iata,
                    "iso_country": iso_country,
                    "iso_region": iso_region,
                    "elevation_ft": elevation_ft,
                    "type": airport_type,
                    "scheduled_service": scheduled_service,
                    "local_code": local_code,
                    "gps_code": gps_code,
                    "faa_lid": faa_lid,
                }
        save_airports(airports)
        print(f"Updated airports.json with {len(airports)} airports.")
    except Exception as e:
        print(f"Failed to update airports: {e}")


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
    parser.add_argument("--no-emoji", action="store_true", help="Disable emoji in weather output")
    parser.add_argument("--setup", action="store_true", help="Create a default config.json")
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

  ./weather.py --no-emoji
      Disable emoji in weather output

  ./weather.py --setup
      Create a default config.json next to the executable
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
            tee = Tee(os.path.join(get_app_dir(), "weather_output.txt"))

        if args.weather_favorites:
            weather_for_favorites(
                show_forecast=args.forecast,
                debug=debug,
                days=days,
                temp_unit_override=temp_unit_override,
                no_emoji=args.no_emoji,
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
        if args.setup:
            setup_default_config()
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
                no_emoji=args.no_emoji,
            )
            return

        print("No command provided. Use --help for usage.")
    finally:
        if tee is not None:
            tee.close()


if __name__ == "__main__":
    main()

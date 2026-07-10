"""
Fetch marine weather data from Open-Meteo API (free, no key required).
"""
import json
import time
import httpx
from datetime import datetime, timedelta


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ports"]


def fetch_weather_for_port(port):
    """Fetch 7-day marine weather for a single port with retry."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": port["lat"],
        "longitude": port["lon"],
        "daily": [
            "wave_height_max",
            "wave_direction_dominant",
            "wind_wave_height_max",
            "wind_wave_direction_dominant",
            "swell_wave_height_max",
            "swell_wave_direction_dominant",
            "wind_speed_10m_max",
            "wind_direction_10m_dominant",
        ],
        "timezone": "Asia/Shanghai",
        "forecast_days": 7,
    }

    max_retries = 2
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = httpx.get(url, params=params, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(3)
    raise last_error


def classify_sea_state(data):
    """Classify sea conditions for human-readable summary."""
    daily = data.get("daily", {})
    if not daily:
        return {}

    today_idx = 0
    result = {}

    # Wave height classification (max wave height)
    wave_key = "wave_height_max"
    if wave_key in daily and today_idx < len(daily[wave_key]):
        wave_h = daily[wave_key][today_idx]
        if wave_h is None:
            result["wave"] = "no data"
        elif wave_h < 1.0:
            result["wave"] = f"slight ({wave_h:.1f}m)"
        elif wave_h < 2.0:
            result["wave"] = f"moderate ({wave_h:.1f}m)"
        elif wave_h < 3.0:
            result["wave"] = f"rough ({wave_h:.1f}m)"
        elif wave_h < 4.0:
            result["wave"] = f"very rough ({wave_h:.1f}m) !!"
        else:
            result["wave"] = f"high ({wave_h:.1f}m) DANGER"

    # Wind speed (Beaufort scale)
    wind_key = "wind_speed_10m_max"
    if wind_key in daily and today_idx < len(daily[wind_key]):
        wind = daily[wind_key][today_idx]
        if wind is None:
            result["wind"] = "no data"
        elif wind < 11:
            result["wind"] = f"light breeze ({wind:.0f} km/h)"
        elif wind < 20:
            result["wind"] = f"moderate ({wind:.0f} km/h)"
        elif wind < 29:
            result["wind"] = f"fresh ({wind:.0f} km/h)"
        elif wind < 39:
            result["wind"] = f"strong ({wind:.0f} km/h) !!"
        elif wind < 50:
            result["wind"] = f"gale ({wind:.0f} km/h) !!"
        else:
            result["wind"] = f"storm ({wind:.0f} km/h) DANGER"

    # 3-day trend
    if wave_key in daily and len(daily[wave_key]) >= 3:
        vals = daily[wave_key][:3]
        if all(v is not None for v in vals):
            if vals[2] > vals[0] * 1.3:
                result["trend"] = "worsening (waves increasing)"
            elif vals[2] < vals[0] * 0.7:
                result["trend"] = "improving (waves decreasing)"
            else:
                result["trend"] = "stable"

    return result


def fetch_all_weather(ports):
    """Fetch weather for all ports, return dict keyed by port code."""
    weather_data = {}
    for port in ports:
        try:
            raw = fetch_weather_for_port(port)
            summary = classify_sea_state(raw)
            weather_data[port["code"]] = {
                "port": port["port"],
                "country": port["country"],
                "raw": raw,
                "summary": summary,
            }
            print(f"  OK {port['port']} ({port['code']}): {summary.get('wave','?')} / {summary.get('wind','?')}")
        except Exception as e:
            print(f"  FAIL {port['port']} ({port['code']}): {e}")
            weather_data[port["code"]] = {
                "port": port["port"],
                "country": port["country"],
                "error": str(e),
                "summary": {},
            }
    return weather_data


if __name__ == "__main__":
    ports = load_ports()
    data = fetch_all_weather(ports)
    print(f"\nFetched weather for {len(data)} ports")

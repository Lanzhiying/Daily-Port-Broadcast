"""
Fetch marine weather data from Open-Meteo API (free, no key required).
"""
import json
import httpx
from datetime import datetime, timedelta


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ports"]


def fetch_weather_for_port(port):
    """Fetch 7-day marine weather for a single port."""
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
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


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
            result["wave"] = "无数据"
        elif wave_h < 1.0:
            result["wave"] = f"微浪 ({wave_h:.1f}m)"
        elif wave_h < 2.0:
            result["wave"] = f"轻浪 ({wave_h:.1f}m)"
        elif wave_h < 3.0:
            result["wave"] = f"中浪 ({wave_h:.1f}m)"
        elif wave_h < 4.0:
            result["wave"] = f"大浪 ({wave_h:.1f}m) ⚠️"
        else:
            result["wave"] = f"巨浪 ({wave_h:.1f}m) 🚫"

    # Wind speed classification
    wind_key = "wind_speed_10m_max"
    if wind_key in daily and today_idx < len(daily[wind_key]):
        wind = daily[wind_key][today_idx]
        if wind is None:
            result["wind"] = "无数据"
        elif wind < 15:
            result["wind"] = f"微风 ({wind:.1f} km/h)"
        elif wind < 30:
            result["wind"] = f"强风 ({wind:.1f} km/h)"
        elif wind < 50:
            result["wind"] = f"大风 ({wind:.1f} km/h) ⚠️"
        else:
            result["wind"] = f"暴风 ({wind:.1f} km/h) 🚫"

    # 3-day trend: increasing or decreasing
    if wave_key in daily and len(daily[wave_key]) >= 3:
        vals = daily[wave_key][:3]
        if all(v is not None for v in vals):
            if vals[2] > vals[0] * 1.3:
                result["trend"] = "📈 未来3天浪高呈上升趋势"
            elif vals[2] < vals[0] * 0.7:
                result["trend"] = "📉 未来3天浪高呈下降趋势"
            else:
                result["trend"] = "➡️ 未来3天海况基本稳定"

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
            print(f"  ✅ {port['port']} ({port['code']}): {summary.get('wave','?')} / {summary.get('wind','?')}")
        except Exception as e:
            print(f"  ❌ {port['port']} ({port['code']}): {e}")
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

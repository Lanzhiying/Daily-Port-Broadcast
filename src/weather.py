"""
Marine + weather data via Open-Meteo.
Marine API for waves, Weather API for wind/gust/precip.
"""
import json, time, httpx


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["ports"]


def fetch_marine(port):
    """Open-Meteo Marine API — waves, swell."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": port["lat"], "longitude": port["lon"],
        "daily": ["wave_height_max", "swell_wave_height_max", "wind_wave_height_max"],
        "timezone": "Asia/Shanghai", "forecast_days": 7,
    }
    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < 2: time.sleep(3)
            else: raise e


def fetch_weather(port):
    """Open-Meteo Weather API — wind, gust, precip, weather_code."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": port["lat"], "longitude": port["lon"],
        "daily": ["wind_speed_10m_max", "wind_gusts_10m_max", "precipitation_sum", "weather_code"],
        "timezone": "Asia/Shanghai", "forecast_days": 7,
    }
    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < 2: time.sleep(3)
            else: raise e


def classify_risk(marine, weather, port_name):
    """Combine marine + weather data into risk assessment."""
    md = marine.get("daily", {}) if marine else {}
    wd = weather.get("daily", {}) if weather else {}
    idx = 0
    r = {}
    alerts = []

    # --- Wave (marine API) ---
    wh = (md.get("wave_height_max") or [None])[idx]
    if wh is not None:
        r["wave"] = f"{wh:.1f}m"
        if wh >= 3.5:
            alerts.append(f"巨浪{wh:.1f}m — 极可能封港")
            r["risk"] = "critical"
        elif wh >= 2.5:
            alerts.append(f"大浪{wh:.1f}m — 吊机/泊位可能暂停")
            r["risk"] = "high"
        elif wh >= 1.5:
            r["risk"] = "moderate"
        else:
            r["risk"] = "low"
    else:
        r["wave"] = "-"

    # --- Swell (marine API) ---
    sw = (md.get("swell_wave_height_max") or [None])[idx]
    if sw is not None:
        r["swell"] = f"{sw:.1f}m"
        if sw >= 3.0:
            alerts.append(f"涌浪{sw:.1f}m — 引航可能暂停")
            if r.get("risk","") not in ("critical",):
                r["risk"] = "high"

    # --- Wind (weather API) ---
    ws = (wd.get("wind_speed_10m_max") or [None])[idx]
    if ws is not None:
        r["wind"] = f"{ws:.0f}km/h"
        if ws >= 50:
            alerts.append(f"暴风{ws:.0f}km/h — 极可能封港")
            r["risk"] = "critical"
        elif ws >= 35:
            alerts.append(f"强风{ws:.0f}km/h — 吊机/引航可能暂停")
            if r.get("risk","") not in ("critical",):
                r["risk"] = "high"
        elif ws >= 25:
            if r.get("risk","") not in ("critical","high"):
                r["risk"] = "moderate"
    else:
        r["wind"] = "-"

    # --- Wind gust (weather API) ---
    wg = (wd.get("wind_gusts_10m_max") or [None])[idx]
    if wg is not None:
        r["gust"] = f"{wg:.0f}km/h"
        if wg >= 70:
            alerts.append(f"阵风{wg:.0f}km/h — 极度危险")

    # --- Precipitation (weather API) ---
    precip = (wd.get("precipitation_sum") or [None])[idx]
    if precip is not None and precip >= 20:
        alerts.append(f"暴雨{precip:.0f}mm — 能见度低")
        r["rain"] = f"{precip:.0f}mm"
    elif precip is not None:
        r["rain"] = f"{precip:.0f}mm"

    # --- Weather code (weather API) ---
    wc = (wd.get("weather_code") or [None])[idx]
    wc_map = {0:"晴",1:"晴",2:"多云",3:"阴",45:"雾",48:"霜雾",
              51:"小雨",53:"中雨",55:"大雨",61:"小雨",63:"中雨",65:"大雨",
              80:"阵雨",82:"强阵雨",95:"雷暴",96:"雷暴+冰雹",99:"强雷暴+冰雹"}
    if wc is not None and wc in wc_map:
        r["weather"] = wc_map[wc]
        if wc in (95,96,99):
            alerts.append("雷暴 — 码头作业极可能暂停")
            r["risk"] = "critical"

    # --- 3-day trend (FIXED: only flag if absolute values are significant) ---
    wh_vals = md.get("wave_height_max", []) if md else []
    if len(wh_vals) >= 3 and all(v is not None for v in wh_vals[:3]):
        now, d1, d2 = wh_vals[0], wh_vals[1], wh_vals[2]
        # Only flag if the peak is > 2.0m (calm seas don't matter)
        max_val = max(now, d1, d2)
        if max_val >= 2.0 and d2 >= now * 1.5:
            r["trend"] = f"急剧恶化 {now:.1f}→{d2:.1f}m"
            if r.get("risk","") not in ("critical","high"):
                r["risk"] = "high"
        elif max_val >= 1.5 and d2 >= now * 1.3:
            r["trend"] = f"恶化 {now:.1f}→{d2:.1f}m"
        elif d2 <= now * 0.6:
            r["trend"] = f"好转 {now:.1f}→{d2:.1f}m"
        else:
            r["trend"] = "稳定"
    else:
        r["trend"] = "-"

    # Risk determination: prioritize weather data, fall back to marine
    if "risk" not in r:
        has_any_data = (r.get("wave") and r.get("wave") != "-") or (r.get("wind") and r.get("wind") != "-")
        r["risk"] = "low" if has_any_data else "unknown"
    r["alerts"] = alerts
    return r


def fetch_all_weather(ports):
    weather_data = {}
    for port in ports:
        try:
            marine = fetch_marine(port)
            weather = fetch_weather(port)
            risk = classify_risk(marine, weather, port["port"])
            weather_data[port["code"]] = {
                "port": port["port"],
                "country": port["country"],
                "risk": risk,
            }
            lvl = risk.get("risk","?")
            flag_map = {"critical":"!!!CRITICAL","high":"!!HIGH","moderate":"MOD","low":"OK","unknown":"NO DATA"}
            flag = flag_map.get(lvl, lvl)
            print(f"  [{flag}] {port['port']}: w={risk.get('wave','?')} "
                  f"wind={risk.get('wind','?')} gust={risk.get('gust','?')} "
                  f"swell={risk.get('swell','?')} trend={risk.get('trend','?')}")
            for a in risk.get("alerts",[]):
                print(f"         {a}")
        except Exception as e:
            print(f"  [FAIL] {port['port']}: {e}")
            weather_data[port["code"]] = {
                "port": port["port"], "country": port["country"],
                "risk": {"risk":"unknown","alerts":[],"wave":"-","wind":"-"},
            }
    return weather_data

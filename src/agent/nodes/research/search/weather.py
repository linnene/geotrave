"""
Module: src.agent.nodes.research.search.weather
Responsibility: Open-Meteo weather forecast API wrapper.
Dependencies: httpx (standard HTTP client)
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from src.utils.logger import get_logger

logger = get_logger("WeatherSearch")

# Open-Meteo free API endpoints
_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather code → simplified Chinese description
_WEATHER_CODES: Dict[int, str] = {
    0: "晴",
    1: "大部晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "冰雹雷暴",
    99: "大冰雹雷暴",
}


async def _geocode(name: str) -> Optional[Dict[str, Any]]:
    """Resolve place name → {name, lat, lon, country} via Open-Meteo geocoding."""

    def _sync():
        try:
            r = httpx.get(
                _GEOCODING_URL,
                params={"name": name, "count": 1, "language": "zh"},
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results")
            if results and len(results) > 0:
                r0 = results[0]
                return {
                    "name": r0.get("name", name),
                    "lat": r0["latitude"],
                    "lon": r0["longitude"],
                    "country": r0.get("country", ""),
                }
        except Exception:
            pass
        return None

    return await asyncio.to_thread(_sync)


async def fetch_weather(
    location: str,
    days: int = 7,
) -> Dict[str, Any]:
    """Fetch daily weather forecast for a location.

    Args:
        location: Place name (e.g. "东京") or "lng,lat" (e.g. "139.65,35.68")
        days: Forecast days (1–16, clamped)

    Returns:
        Dict with location, forecast_days, and daily fields.
        Error dict with "error" key on failure.
    """
    days = max(1, min(days, 16))

    # Parse coordinates vs place name
    lat: Optional[float] = None
    lon: Optional[float] = None
    place_name: str = location

    import re

    coord_match = re.match(
        r"^\s*([+-]?\d+\.?\d*)\s*[,，]\s*([+-]?\d+\.?\d*)\s*$", location
    )
    if coord_match:
        lon = float(coord_match.group(1))
        lat = float(coord_match.group(2))
    else:
        geo = await _geocode(location)
        if geo is None:
            logger.warning("Geocode failed for: %s", location)
            return {"error": f"无法解析地点: {location}"}
        lat = geo["lat"]
        lon = geo["lon"]
        place_name = geo["name"]

    # Fetch forecast
    daily_params = (
        "temperature_2m_max,temperature_2m_min,precipitation_sum,"
        "precipitation_probability_max,weathercode,windspeed_10m_max"
    )

    def _sync_fetch():
        try:
            r = httpx.get(
                _FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": daily_params,
                    "forecast_days": days,
                    "timezone": "auto",
                },
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("Open-Meteo forecast failed: %s", e)
            return None

    data = await asyncio.to_thread(_sync_fetch)
    if data is None:
        return {"error": f"天气数据获取失败: {place_name}"}

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    precip_prob = daily.get("precipitation_probability_max", [])
    weather_codes = daily.get("weathercode", [])
    winds = daily.get("windspeed_10m_max", [])

    forecast: List[Dict[str, Any]] = []
    for i in range(len(dates)):
        code = int(weather_codes[i]) if i < len(weather_codes) else -1
        forecast.append(
            {
                "date": dates[i] if i < len(dates) else "",
                "temp_max": temps_max[i] if i < len(temps_max) else None,
                "temp_min": temps_min[i] if i < len(temps_min) else None,
                "precip_mm": precip[i] if i < len(precip) else None,
                "precip_prob": precip_prob[i] if i < len(precip_prob) else None,
                "weather": _WEATHER_CODES.get(code, f"未知({code})"),
                "wind_kmh": winds[i] if i < len(winds) else None,
            }
        )

    logger.info(
        "Weather: location=%s days=%d fetched=%d",
        place_name, days, len(forecast),
    )

    return {
        "location": place_name,
        "lat": lat,
        "lon": lon,
        "forecast_days": days,
        "daily": forecast,
    }

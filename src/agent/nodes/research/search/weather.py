"""
Module: src.agent.nodes.research.search.weather
Responsibility: Open-Meteo weather forecast API wrapper.
Dependencies: httpx (standard HTTP client)
"""

import asyncio
import re
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

# CJK/Chinese → English city name mapping for places Open-Meteo may not index
# under their Chinese names. Ordered by region for easy maintenance.
_CITY_NAME_MAP: Dict[str, str] = {
    # ── 日本 ──
    "札幌": "Sapporo",
    "函馆": "Hakodate",
    "小樽": "Otaru",
    "富良野": "Furano",
    "旭川": "Asahikawa",
    "东京": "Tokyo",
    "新宿": "Shinjuku",
    "涩谷": "Shibuya",
    "银座": "Ginza",
    "大阪": "Osaka",
    "京都": "Kyoto",
    "奈良": "Nara",
    "神户": "Kobe",
    "横滨": "Yokohama",
    "名古屋": "Nagoya",
    "福冈": "Fukuoka",
    "冲绳": "Okinawa",
    "那霸": "Naha",
    "鹿儿岛": "Kagoshima",
    "广岛": "Hiroshima",
    "仙台": "Sendai",
    "金泽": "Kanazawa",
    "镰仓": "Kamakura",
    "箱根": "Hakone",
    "轻井泽": "Karuizawa",
    "日光": "Nikko",
    "姬路": "Himeji",
    "长崎": "Nagasaki",
    "熊本": "Kumamoto",
    "北海道": "Hokkaido",
    # ── 韩国 ──
    "首尔": "Seoul",
    "釜山": "Busan",
    "济州": "Jeju",
    "仁川": "Incheon",
    # ── 东南亚 ──
    "曼谷": "Bangkok",
    "普吉": "Phuket",
    "清迈": "Chiang Mai",
    "芭提雅": "Pattaya",
    "巴厘岛": "Bali",
    "新加坡": "Singapore",
    "吉隆坡": "Kuala Lumpur",
    "河内": "Hanoi",
    "胡志明": "Ho Chi Minh City",
    "岘港": "Da Nang",
    # ── 欧洲 ──
    "巴黎": "Paris",
    "伦敦": "London",
    "罗马": "Rome",
    "威尼斯": "Venice",
    "佛罗伦萨": "Florence",
    "米兰": "Milan",
    "巴塞罗那": "Barcelona",
    "马德里": "Madrid",
    "布拉格": "Prague",
    "维也纳": "Vienna",
    "布达佩斯": "Budapest",
    "阿姆斯特丹": "Amsterdam",
    "苏黎世": "Zurich",
    "慕尼黑": "Munich",
    "柏林": "Berlin",
    "圣托里尼": "Santorini",
    # ── 北美 ──
    "纽约": "New York",
    "洛杉矶": "Los Angeles",
    "旧金山": "San Francisco",
    "拉斯维加斯": "Las Vegas",
    "芝加哥": "Chicago",
    "温哥华": "Vancouver",
    "多伦多": "Toronto",
    # ── 大洋洲 ──
    "悉尼": "Sydney",
    "墨尔本": "Melbourne",
    "黄金海岸": "Gold Coast",
    "奥克兰": "Auckland",
    # ── 港澳台 ──
    "台北": "Taipei",
    "台中": "Taichung",
    "高雄": "Kaohsiung",
    "香港": "Hong Kong",
    "澳门": "Macau",
}


def _resolve_candidates(name: str) -> List[str]:
    """Build geocoding name candidates: original, mapped, and partial matches."""
    candidates = [name]
    # Exact CJK → English mapping
    mapped = _CITY_NAME_MAP.get(name.strip())
    if mapped and mapped not in candidates:
        candidates.append(mapped)
    return candidates


async def _geocode(name: str) -> Optional[Dict[str, Any]]:
    """Resolve place name → {name, lat, lon, country} via Open-Meteo geocoding.

    Tries multiple name candidates (original + mapped English name),
    each with multiple language hints (zh, en, native). Returns the first
    successful result or None if all attempts fail.
    """
    candidates = _resolve_candidates(name)
    languages = ["zh", "en", None]  # None = no language hint

    def _try_once(candidate: str, lang: str | None) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"name": candidate, "count": 1}
        if lang:
            params["language"] = lang
        try:
            r = httpx.get(_GEOCODING_URL, params=params, timeout=5)
            r.raise_for_status()
            data = r.json()
            results = data.get("results") if isinstance(data, dict) else None
            if results and len(results) > 0:
                r0 = results[0]
                return {
                    "name": r0.get("name", candidate),
                    "lat": r0.get("latitude"),
                    "lon": r0.get("longitude"),
                    "country": r0.get("country", ""),
                }
        except Exception as exc:
            logger.debug("Geocode attempt failed (candidate=%r lang=%r): %s", candidate, lang, exc)
        return None

    for candidate in candidates:
        for lang in languages:
            result = await asyncio.to_thread(_try_once, candidate, lang)
            if result is not None and result.get("lat") is not None:
                if candidate != name:
                    logger.info("Geocode resolved via mapping: %r → %r", name, candidate)
                return result

    logger.warning("Geocode failed for %r (tried candidates: %s)", name, candidates)
    return None


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

    lat: Optional[float] = None
    lon: Optional[float] = None
    place_name: str = location

    coord_match = re.match(
        r"^\s*([+-]?\d+\.?\d*)\s*[,，]\s*([+-]?\d+\.?\d*)\s*$", location
    )
    if coord_match:
        lon = float(coord_match.group(1))
        lat = float(coord_match.group(2))
    else:
        geo = await _geocode(location)
        if geo is None:
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
        raw_code = weather_codes[i] if i < len(weather_codes) else None
        code = int(raw_code) if raw_code is not None else -1
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

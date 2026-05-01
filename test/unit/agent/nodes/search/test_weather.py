"""
Test Suite: weather_search — Open-Meteo forecast + tool handler
Mapping: /src/agent/nodes/research/search/weather.py
Priority: P1 — External weather API tool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import SearchTask, RetrievalMetadata


# =============================================================================
# P1 — fetch_weather (Open-Meteo)
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_weather_by_coordinates():
    """Coordinates → Open-Meteo forecast returned with parsed daily fields."""
    from src.agent.nodes.research.search.weather import fetch_weather

    mock_response = {
        "daily": {
            "time": ["2026-05-01", "2026-05-02"],
            "temperature_2m_max": [22.5, 19.0],
            "temperature_2m_min": [14.0, 12.5],
            "precipitation_sum": [0.0, 5.2],
            "precipitation_probability_max": [10, 70],
            "weathercode": [0, 61],
            "windspeed_10m_max": [12.0, 25.3],
        }
    }

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = await fetch_weather("139.65,35.68", days=2)

    assert result["location"] == "139.65,35.68"
    assert result["forecast_days"] == 2
    assert len(result["daily"]) == 2
    assert result["daily"][0]["date"] == "2026-05-01"
    assert result["daily"][0]["temp_max"] == 22.5
    assert result["daily"][0]["temp_min"] == 14.0
    assert result["daily"][0]["precip_mm"] == 0.0
    assert result["daily"][0]["precip_prob"] == 10
    assert result["daily"][0]["weather"] == "晴"
    assert result["daily"][0]["wind_kmh"] == 12.0
    assert result["daily"][1]["weather"] == "小雨"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_weather_geocode_place_name():
    """Place name triggers geocoding → coordinates → forecast."""
    from src.agent.nodes.research.search.weather import fetch_weather

    geo_response = {
        "results": [
            {"name": "东京", "latitude": 35.68, "longitude": 139.65, "country": "日本"}
        ]
    }

    forecast_response = {
        "daily": {
            "time": ["2026-05-01"],
            "temperature_2m_max": [20.0],
            "temperature_2m_min": [15.0],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [5],
            "weathercode": [1],
            "windspeed_10m_max": [10.0],
        }
    }

    with patch("httpx.get") as mock_get:
        mock_geo = MagicMock()
        mock_geo.json.return_value = geo_response
        mock_geo.raise_for_status.return_value = None

        mock_fc = MagicMock()
        mock_fc.json.return_value = forecast_response
        mock_fc.raise_for_status.return_value = None

        mock_get.side_effect = [mock_geo, mock_fc]

        result = await fetch_weather("东京", days=1)

    assert result["location"] == "东京"
    assert len(result["daily"]) == 1
    assert result["daily"][0]["temp_max"] == 20.0


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_weather_geocode_failure():
    """Geocode returns no results → error dict."""
    from src.agent.nodes.research.search.weather import fetch_weather

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("Not found")
        mock_get.return_value = mock_resp

        result = await fetch_weather("不存在的奇怪地名xyz")

    assert "error" in result
    assert "无法解析" in result["error"]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_weather_forecast_http_failure():
    """Geocode succeeds but forecast HTTP fails → error dict."""
    from src.agent.nodes.research.search.weather import fetch_weather

    geo_response = {
        "results": [
            {"name": "札幌", "latitude": 43.06, "longitude": 141.35, "country": "日本"}
        ]
    }

    with patch("httpx.get") as mock_get:
        mock_geo = MagicMock()
        mock_geo.json.return_value = geo_response
        mock_geo.raise_for_status.return_value = None

        mock_fc = MagicMock()
        mock_fc.raise_for_status.side_effect = Exception("Server error")

        mock_get.side_effect = [mock_geo, mock_fc]

        result = await fetch_weather("札幌")

    assert "error" in result
    assert "获取失败" in result["error"]


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_fetch_weather_clamps_days():
    """days < 1 clamped to 1; days > 16 clamped to 16."""
    from src.agent.nodes.research.search.weather import fetch_weather

    forecast_response = {
        "daily": {
            "time": ["2026-05-01"],
            "temperature_2m_max": [20.0],
            "temperature_2m_min": [10.0],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [0],
            "weathercode": [0],
            "windspeed_10m_max": [5.0],
        }
    }

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = forecast_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        # days=0 → clamped to 1
        r0 = await fetch_weather("0,0", days=0)
        assert r0["forecast_days"] == 1

        # days=999 → clamped to 16
        r999 = await fetch_weather("0,0", days=999)
        assert r999["forecast_days"] == 16


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_fetch_weather_unknown_weather_code_falls_back():
    """WMO code not in lookup table renders '未知(N)'."""
    from src.agent.nodes.research.search.weather import fetch_weather

    forecast_response = {
        "daily": {
            "time": ["2026-05-01"],
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [18.0],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [0],
            "weathercode": [999],
            "windspeed_10m_max": [8.0],
        }
    }

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = forecast_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = await fetch_weather("0,0", days=1)

    assert "未知(999)" in result["daily"][0]["weather"]


# =============================================================================
# P1 — execute_weather_search (tool handler)
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_weather_search_tool_handler_success():
    """Handler calls fetch_weather and wraps result in RetrievalMetadata."""
    from src.agent.nodes.research.search.tools import execute_weather_search

    mock_payload = {
        "location": "大阪",
        "lat": 34.69,
        "lon": 135.50,
        "forecast_days": 3,
        "daily": [
            {"date": "2026-05-01", "temp_max": 25.0, "temp_min": 16.0,
             "precip_mm": 0.0, "precip_prob": 5, "weather": "晴", "wind_kmh": 10.0},
        ],
    }

    task = SearchTask(
        tool_name="weather_search",
        dimension="weather",
        parameters={"location": "大阪", "days": "3"},
        rationale="测试天气查询",
    )

    with patch(
        "src.agent.nodes.research.search.weather.fetch_weather",
        new=AsyncMock(return_value=mock_payload),
    ):
        result = await execute_weather_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert result.payload["location"] == "大阪"
    assert result.payload["forecast_days"] == 3
    assert len(result.payload["daily"]) == 1
    assert "weather_" in result.hash_key
    assert result.relevance_score == 1.0


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_weather_search_missing_location():
    """Missing required 'location' parameter raises ValueError."""
    from src.agent.nodes.research.search.tools import execute_weather_search

    task = SearchTask(
        tool_name="weather_search",
        dimension="weather",
        parameters={"days": "5"},
        rationale="测试缺少location",
    )

    with pytest.raises(ValueError, match="缺少必填参数"):
        await execute_weather_search(task)


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_weather_search_error_payload():
    """fetch_weather returns error dict → handler wraps it in payload."""
    from src.agent.nodes.research.search.tools import execute_weather_search

    mock_payload = {"error": "无法解析地点: nowhere"}

    task = SearchTask(
        tool_name="weather_search",
        dimension="weather",
        parameters={"location": "nowhere"},
        rationale="测试错误payload",
    )

    with patch(
        "src.agent.nodes.research.search.weather.fetch_weather",
        new=AsyncMock(return_value=mock_payload),
    ):
        result = await execute_weather_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert "error" in result.payload

"""
Test Suite: Search Tool Handlers
Mapping: /src/agent/nodes/search/tools.py
Priority: P1 - Tool Execution Correctness
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import SearchTask, RetrievalMetadata


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_pool(fetch_rows, fetchval_values=None):
    """Build a mock asyncpg Pool where acquire() returns an async context manager."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = fetch_rows
    if fetchval_values is not None:
        mock_conn.fetchval = AsyncMock(side_effect=fetchval_values)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    return mock_pool


# ---------------------------------------------------------------------------
# _parse_lnglat
# ---------------------------------------------------------------------------

@pytest.mark.priority("P0")
def test_parse_lnglat_valid():
    """
    Priority: P0
    Description: Valid 'lng,lat' string returns (lng, lat) float tuple.
    """
    from src.agent.nodes.search.tools import _parse_lnglat

    lng, lat = _parse_lnglat("141.35, 43.07")
    assert lng == 141.35, f"经度应为 141.35，实际: {lng}"
    assert lat == 43.07, f"纬度应为 43.07，实际: {lat}"


@pytest.mark.priority("P0")
def test_parse_lnglat_no_spaces():
    """
    Priority: P0
    Description: Parsing works without spaces around comma.
    """
    from src.agent.nodes.search.tools import _parse_lnglat

    lng, lat = _parse_lnglat("139.76,35.68")
    assert lng == 139.76, f"经度应为 139.76，实际: {lng}"
    assert lat == 35.68, f"纬度应为 35.68，实际: {lat}"


@pytest.mark.priority("P1")
def test_parse_lnglat_invalid_format():
    """
    Priority: P1
    Description: Invalid coordinate string raises ValueError.
    """
    from src.agent.nodes.search.tools import _parse_lnglat

    invalid_inputs = ["141.35", "141.35,", "a,b"]
    for val in invalid_inputs:
        try:
            _parse_lnglat(val)
            pytest.fail(f"输入 '{val}' 应触发 ValueError，但未触发")
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# _resolve_location & _geocode
# ---------------------------------------------------------------------------

@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_resolve_location_coords():
    """
    Priority: P1
    Description: _resolve_location returns coordinates directly when given 'lng,lat'.
    """
    from src.agent.nodes.search.tools import _resolve_location

    lng, lat = await _resolve_location("141.35, 43.07")
    assert lng == 141.35, f"经度应为 141.35，实际: {lng}"
    assert lat == 43.07, f"纬度应为 43.07，实际: {lat}"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_geocode_by_name():
    """
    Priority: P1
    Description: _resolve_location falls back to _geocode for place names.
    """
    from src.agent.nodes.search.tools import _resolve_location

    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, k: {"lng": 141.35, "lat": 43.07}[k]
    mock_pool = _mock_pool(fetch_rows=[], fetchval_values=None)
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_row
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        lng, lat = await _resolve_location("札幌站")

    assert lng == 141.35, f"经度应为 141.35，实际: {lng}"
    assert lat == 43.07, f"纬度应为 43.07，实际: {lat}"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_geocode_suffix_stripping():
    """
    Priority: P1
    Description: _geocode strips common suffixes when exact/fuzzy match fails.
    E.g. "札幌駅" matches station named "札幌" after stripping "駅".
    """
    from src.agent.nodes.search.tools import _resolve_location

    mock_pool = _mock_pool(fetch_rows=[], fetchval_values=None)
    # First call: exact match "札幌駅" → None
    # Second call: fuzzy match "%札幌駅%" → None
    # Third call: stripped "札幌" exact match → success
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(side_effect=[
        None,                           # exact "札幌駅"
        None,                           # fuzzy "%札幌駅%"
        MagicMock(__getitem__=lambda self, k: {"lng": 141.3509, "lat": 43.0686}[k]),  # stripped "札幌"
    ])
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        lng, lat = await _resolve_location("札幌駅")

    assert lng == 141.3509, f"经度应为 141.3509，实际: {lng}"
    assert lat == 43.0686, f"纬度应为 43.0686，实际: {lat}"


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_geocode_not_found():
    """
    Priority: P2
    Description: _geocode raises ValueError when place name not found.
    """
    from src.agent.nodes.search.tools import _resolve_location

    mock_pool = _mock_pool(fetch_rows=[], fetchval_values=None)
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None  # No match
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        with pytest.raises(ValueError, match="无法找到地点"):
            await _resolve_location("不存在的奇怪地名XYZ123")


# ---------------------------------------------------------------------------
# spatial_search (mock DB)
# ---------------------------------------------------------------------------

@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_spatial_search_returns_pois():
    """
    Priority: P1
    Description: spatial_search queries DB and returns POI results in payload.
    """
    from src.agent.nodes.search.tools import execute_spatial_search

    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, k: {
        "name": "札幌駅", "category": "transport",
        "sub_category": None, "lng": 141.35, "lat": 43.07, "dist_m": 50.0,
    }[k]

    mock_pool = _mock_pool(fetch_rows=[mock_row])

    task = SearchTask(
        tool_name="spatial_search",
        dimension="attraction",
        parameters={"center": "141.35,43.07", "radius_m": "1000", "limit": "5"},
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(return_value=(141.35, 43.07))), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await execute_spatial_search(task)

    assert isinstance(result, RetrievalMetadata), (
        f"返回值应为 RetrievalMetadata，实际: {type(result).__name__}"
    )
    assert result.payload["total"] == 1, (
        f"应返回 1 条 POI，实际: {result.payload['total']}"
    )
    assert result.payload["pois"][0]["name"] == "札幌駅", (
        f"POI 名称应为 '札幌駅'，实际: {result.payload['pois'][0]['name']}"
    )
    assert result.relevance_score == 1.0, (
        f"空间检索结果相关性评分应为 1.0，实际: {result.relevance_score}"
    )


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_spatial_search_empty_result():
    """
    Priority: P2
    Description: spatial_search handles empty result set gracefully.
    """
    from src.agent.nodes.search.tools import execute_spatial_search

    mock_pool = _mock_pool(fetch_rows=[])

    task = SearchTask(
        tool_name="spatial_search",
        dimension="attraction",
        parameters={"center": "0.0,0.0", "radius_m": "10", "limit": "10"},
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(return_value=(0.0, 0.0))), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await execute_spatial_search(task)

    assert result.payload["total"] == 0, (
        f"空结果集的 total 应为 0，实际: {result.payload['total']}"
    )
    assert len(result.payload["pois"]) == 0, (
        f"空结果集的 pois 列表应为空，实际长度: {len(result.payload['pois'])}"
    )


# ---------------------------------------------------------------------------
# route_search (mock DB)
# ---------------------------------------------------------------------------

@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_route_search_shortest_path():
    """
    Priority: P1
    Description: route_search shortest mode returns distance and walk time.
    """
    from src.agent.nodes.search.tools import execute_route_search

    edge_rows = [
        {"cost": 120.0, "agg_cost": 0},
        {"cost": 80.0, "agg_cost": 120.0},
    ]
    mock_pool = _mock_pool(fetch_rows=edge_rows, fetchval_values=[42, 99])

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={
            "origin": "141.35,43.07",
            "destination": "141.36,43.08",
            "mode": "shortest",
        },
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(side_effect=[(141.35, 43.07), (141.36, 43.08)])), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await execute_route_search(task)

    assert result.payload["mode"] == "shortest", (
        f"模式应为 shortest，实际: {result.payload['mode']}"
    )
    assert result.payload["distance_km"] == 0.2, (
        f"总距离应为 0.2 km (200m)，实际: {result.payload['distance_km']}"
    )
    assert result.payload["edge_count"] == 2, (
        f"边数应为 2，实际: {result.payload['edge_count']}"
    )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_route_search_isochrone():
    """
    Priority: P1
    Description: route_search isochrone mode returns reachable node count.
    """
    from src.agent.nodes.search.tools import execute_route_search

    iso_rows = [
        {"agg_cost": 100.0},
        {"agg_cost": 250.0},
        {"agg_cost": 500.0},
    ]
    mock_pool = _mock_pool(fetch_rows=iso_rows, fetchval_values=[42])

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={
            "origin": "141.35,43.07",
            "mode": "isochrone",
            "isochrone_minutes": "15",
        },
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(return_value=(141.35, 43.07))), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await execute_route_search(task)

    assert result.payload["mode"] == "isochrone", (
        f"模式应为 isochrone，实际: {result.payload['mode']}"
    )
    assert result.payload["reachable_nodes"] == 3, (
        f"可达节点数应为 3，实际: {result.payload['reachable_nodes']}"
    )
    assert result.payload["max_distance_m"] == 500.0, (
        f"最大距离应为 500.0m，实际: {result.payload['max_distance_m']}"
    )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_route_search_invalid_mode():
    """
    Priority: P1
    Description: Unsupported mode raises ValueError.
    """
    from src.agent.nodes.search.tools import execute_route_search

    mock_pool = _mock_pool(fetch_rows=[], fetchval_values=[42])

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={
            "origin": "141.35,43.07",
            "mode": "unknown_mode",
        },
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(return_value=(141.35, 43.07))), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        with pytest.raises(ValueError, match="Unsupported route_search mode"):
            await execute_route_search(task)


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_route_search_shortest_missing_destination():
    """
    Priority: P1
    Description: shortest mode without destination raises ValueError.
    """
    from src.agent.nodes.search.tools import execute_route_search

    mock_pool = _mock_pool(fetch_rows=[], fetchval_values=[42])

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={"origin": "141.35,43.07", "mode": "shortest"},
        rationale="test",
    )

    with patch("src.agent.nodes.search.tools._resolve_location", new=AsyncMock(return_value=(141.35, 43.07))), \
         patch("src.agent.nodes.search.tools.get_pool", new=AsyncMock(return_value=mock_pool)):
        with pytest.raises(ValueError, match="Unsupported route_search mode"):
            await execute_route_search(task)

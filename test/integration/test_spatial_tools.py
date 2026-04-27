"""
Integration Test Suite: PostGIS Spatial Tools (requires live database)
Mapping: /src/agent/nodes/search/tools.py, /src/database/postgis/
Priority: P0 — Data-Layer Correctness
"""

import os
import pytest
from src.agent.state import SearchTask

DSN = os.getenv("POSTGIS_DSN", "")
needs_db = pytest.mark.skipif(
    not DSN, reason="POSTGIS_DSN not set — skip integration test"
)


def _reset_pool():
    """Drop stale pool reference. Each test gets a new event loop, so old connections
    cannot be cleanly closed from the current loop."""
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = None


# ---------------------------------------------------------------------------
# P0 — spatial_search core path
# ---------------------------------------------------------------------------

@needs_db
@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_spatial_search_returns_real_data():
    """
    Priority: P0
    Description: spatial_search returns actual POI data from live PostGIS.
    """
    from src.agent.nodes.search.tools import execute_spatial_search

    _reset_pool()

    task = SearchTask(
        tool_name="spatial_search",
        dimension="attraction",
        parameters={"center": "141.35,43.07", "radius_m": "1000", "limit": "10"},
        rationale="integration test",
    )
    result = await execute_spatial_search(task)

    assert result.payload["total"] > 0, (
        f"札幌站 1km 内应有 POI，实际 total: {result.payload['total']}"
    )
    assert len(result.payload["pois"]) == result.payload["total"], (
        f"pois 列表长度 ({len(result.payload['pois'])}) 应与 total ({result.payload['total']}) 一致"
    )
    assert result.relevance_score == 1.0, (
        f"空间检索结果评分应为 1.0，实际: {result.relevance_score}"
    )

    # Verify POI structure
    poi = result.payload["pois"][0]
    for key in ("name", "category", "lng", "lat", "dist_m"):
        assert key in poi, f"POI 记录应包含 '{key}' 字段，实际 keys: {list(poi.keys())}"


@needs_db
@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_spatial_search_category_filter():
    """
    Priority: P0
    Description: Category filter correctly matches both amenity and tourism tags.
    """
    from src.agent.nodes.search.tools import execute_spatial_search

    _reset_pool()

    task = SearchTask(
        tool_name="spatial_search",
        dimension="dining",
        parameters={"center": "141.35,43.07", "radius_m": "3000", "category": "restaurant", "limit": "20"},
        rationale="integration test",
    )
    result = await execute_spatial_search(task)

    assert result.payload["total"] > 0, (
        f"札幌站 3km 内应有餐厅，实际 total: {result.payload['total']}"
    )
    for poi in result.payload["pois"]:
        category_match = poi["category"] == "restaurant" or poi["sub_category"] == "restaurant"
        assert category_match, (
            f"过滤结果应全部为 restaurant，实际 category='{poi['category']}', sub_category='{poi['sub_category']}'"
        )


# ---------------------------------------------------------------------------
# P0 — route_search core path
# ---------------------------------------------------------------------------

@needs_db
@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_route_search_shortest_path():
    """
    Priority: P0
    Description: route_search shortest mode computes real shortest path.
    """
    from src.agent.nodes.search.tools import execute_route_search

    _reset_pool()

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={
            "origin": "141.35,43.07",
            "destination": "141.356,43.06",
            "mode": "shortest",
        },
        rationale="integration test",
    )
    result = await execute_route_search(task)

    assert result.payload["mode"] == "shortest", (
        f"模式应为 shortest，实际: {result.payload['mode']}"
    )
    assert result.payload["distance_km"] > 0, (
        f"距离应 > 0 km，实际: {result.payload['distance_km']}"
    )
    assert result.payload["edge_count"] > 0, (
        f"至少应经过 1 条边，实际: {result.payload['edge_count']}"
    )
    # Walk speed 5 km/h validation
    expected_walk_min = round((result.payload["distance_km"] * 1000) / 83.3, 1)
    assert result.payload["walk_min"] == expected_walk_min, (
        f"步行时间应为 {expected_walk_min} min (5km/h)，实际: {result.payload['walk_min']}"
    )


@needs_db
@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_route_search_isochrone():
    """
    Priority: P0
    Description: route_search isochrone mode returns reachable nodes.
    """
    from src.agent.nodes.search.tools import execute_route_search

    _reset_pool()

    task = SearchTask(
        tool_name="route_search",
        dimension="transportation",
        parameters={
            "origin": "141.35,43.07",
            "mode": "isochrone",
            "isochrone_minutes": "15",
        },
        rationale="integration test",
    )
    result = await execute_route_search(task)

    assert result.payload["mode"] == "isochrone", (
        f"模式应为 isochrone，实际: {result.payload['mode']}"
    )
    assert result.payload["reachable_nodes"] > 0, (
        f"15min 等时圈应有可达节点，实际: {result.payload['reachable_nodes']}"
    )
    # 5 km/h * 15 min = 1250 m theoretical max
    assert result.payload["max_distance_m"] <= 1300, (
        f"15min 步行最大距离不应超过 1300m，实际: {result.payload['max_distance_m']}m"
    )
    assert result.payload["max_distance_m"] >= 500, (
        f"15min 步行最大距离应 >= 500m，实际: {result.payload['max_distance_m']}m"
    )

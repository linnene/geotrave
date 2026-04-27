"""
Tool definitions and registered functions for Search node.

Tools are registered via the @register_tool decorator, which automatically
populates TOOL_METADATA (used by QueryGenerator) and TOOL_DISPATCH (used by
Search node). No manual metadata list is required.
"""

import functools
import json
import time
from typing import Any, Dict, List

from src.agent.state import RetrievalMetadata, SearchTask
from src.database.postgis import get_pool
from src.utils.logger import get_logger

logger = get_logger("SearchTools")

# ---------------------------------------------------------------------------
# Auto‑registration machinery
# ---------------------------------------------------------------------------

TOOL_METADATA: List[Dict[str, Any]] = []
TOOL_DISPATCH: Dict[str, Any] = {}


def register_tool(name: str, description: str, parameters: Dict[str, str]):
    """
    Decorator that automatically registers a tool's metadata and dispatch entry.
    After decoration the tool is immediately usable by both the QueryGenerator
    (via TOOL_METADATA) and the Search node (via TOOL_DISPATCH).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(task: SearchTask) -> RetrievalMetadata:
            logger.info(f"Executing tool '{name}' with params: {task.parameters}")
            return await func(task)

        TOOL_METADATA.append({
            "name": name,
            "description": description,
            "parameters": parameters,
        })
        TOOL_DISPATCH[name] = wrapper
        logger.debug(f"Registered tool: {name}")
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Registered tool implementations (mock outputs)
# ---------------------------------------------------------------------------

@register_tool(
    name="web_search",
    description="搜索互联网获取最新旅游信息、攻略、评价等。",
    parameters={"query": "string (搜索关键词)"},
)
async def execute_web_search(task: SearchTask) -> RetrievalMetadata:
    """
    Mock implementation of web search.
    """
    params = task.parameters
    query = params.get("query", "mock query")

    logger.info(f"Mock web search for: {query}")

    hash_key = f"mock_web_{query}_{int(time.time() * 1000)}"
    return RetrievalMetadata(
        hash_key=hash_key,
        source=f"web_search: {query}",
        relevance_score=0.8,
    )


# ---------------------------------------------------------------------------
# Additional tool stubs (declared but not yet implemented)
# ---------------------------------------------------------------------------

@register_tool(
    name="flight_api",
    description="查询实时航班信息、票价（尚未实现）。",
    parameters={
        "origin": "string (出发地代码/名称)",
        "destination": "string (目的地代码/名称)",
        "date": "string (出发日期)",
    },
)
async def execute_flight_search(task: SearchTask) -> RetrievalMetadata:
    """
    Placeholder for flight API search.
    """
    raise NotImplementedError("Flight search is not yet implemented.")


@register_tool(
    name="hotel_api",
    description="查询酒店可用性、价格（尚未实现）。",
    parameters={
        "destination": "string (目的地)",
        "check_in": "string (入住日期)",
        "check_out": "string (退房日期)",
        "guests": "int (入住人数)",
    },
)
async def execute_hotel_search(task: SearchTask) -> RetrievalMetadata:
    """
    Placeholder for hotel database search.
    """
    raise NotImplementedError("Hotel search is not yet implemented.")


# ---------------------------------------------------------------------------
# PostGIS spatial tools (Phase 3)
# ---------------------------------------------------------------------------

def _parse_lnglat(raw: str) -> tuple[float, float]:
    """Parse 'lng,lat' string into (lng, lat) floats."""
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinate format '{raw}', expected 'lng,lat'")
    return float(parts[0]), float(parts[1])


@register_tool(
    name="spatial_search",
    description="基于地理位置检索 POI，支持空间范围过滤与类别筛选。查询半径内的餐厅、景点、住宿等。",
    parameters={
        "center": "string (中心点坐标 'lng,lat')",
        "radius_m": "int (搜索半径，米)",
        "category": "string (可选: accommodation/dining/attraction/transport)",
        "limit": "int (返回条数上限，默认 10)",
    },
)
async def execute_spatial_search(task: SearchTask) -> RetrievalMetadata:
    params = task.parameters
    center = params.get("center", "")
    radius_m = int(params.get("radius_m", 1000))
    category = params.get("category")
    limit = int(params.get("limit", 10))

    lng, lat = _parse_lnglat(center)
    pool = await get_pool()

    query = """
        SELECT name, category, sub_category, lng, lat,
               ST_Distance(geom::geography,
                   ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS dist_m
        FROM geotrave_poi
        WHERE ST_DWithin(geom::geography,
                   ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3)
        ORDER BY dist_m
        LIMIT $4
    """
    args: list = [lng, lat, radius_m, limit]

    if category:
        query = """
            SELECT name, category, sub_category, lng, lat,
                   ST_Distance(geom::geography,
                       ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS dist_m
            FROM geotrave_poi
            WHERE ST_DWithin(geom::geography,
                       ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3)
              AND (category = $4 OR sub_category = $4)
            ORDER BY dist_m
            LIMIT $5
        """
        args = [lng, lat, radius_m, category, limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)

    results = [
        {
            "name": r["name"],
            "category": r["category"],
            "sub_category": r["sub_category"],
            "lng": r["lng"],
            "lat": r["lat"],
            "dist_m": round(r["dist_m"], 1),
        }
        for r in rows
    ]

    return RetrievalMetadata(
        hash_key=f"spatial_{center}_{radius_m}_{category}_{int(time.time() * 1000)}",
        source=f"spatial_search({center}, {radius_m}m)",
        relevance_score=1.0,
        payload={
            "center": center,
            "radius_m": radius_m,
            "category": category,
            "total": len(results),
            "pois": results,
        },
    )


@register_tool(
    name="route_search",
    description="计算两点间最短路径距离/时间，或某点的等时圈范围。",
    parameters={
        "origin": "string (起点 'lng,lat')",
        "destination": "string (可选: 终点 'lng,lat')",
        "mode": "string ('shortest' | 'isochrone')",
        "isochrone_minutes": "int (等时圈分钟数，默认 15)",
    },
)
async def execute_route_search(task: SearchTask) -> RetrievalMetadata:
    params = task.parameters
    origin = params.get("origin", "")
    destination = params.get("destination")
    mode = params.get("mode", "shortest")
    isochrone_minutes = int(params.get("isochrone_minutes", 15))

    pool = await get_pool()

    async with pool.acquire() as conn:
        if mode == "shortest" and destination:
            org_lng, org_lat = _parse_lnglat(origin)
            dst_lng, dst_lat = _parse_lnglat(destination)

            # Find nearest routing vertices
            src = await conn.fetchval(
                """
                SELECT id FROM routing_network_vertices_pgr
                ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
                LIMIT 1
                """, org_lng, org_lat)
            tgt = await conn.fetchval(
                """
                SELECT id FROM routing_network_vertices_pgr
                ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
                LIMIT 1
                """, dst_lng, dst_lat)

            # Run Dijkstra
            routes = await conn.fetch(
                """
                SELECT seq, node, edge, cost, agg_cost
                FROM pgr_dijkstra(
                    'SELECT osm_id AS id, source, target, length_m AS cost, length_m AS reverse_cost FROM routing_network',
                    $1::bigint, $2::bigint, directed := false
                )
                """, src, tgt)

            total_dist_m = sum(r["cost"] for r in routes)
            total_dist_km = round(total_dist_m / 1000, 2)
            walk_min = round(total_dist_m / 83.3, 1)  # 5 km/h

            return RetrievalMetadata(
                hash_key=f"route_{origin}_{destination}_{int(time.time() * 1000)}",
                source=f"route_search({origin}→{destination})",
                relevance_score=1.0,
                payload={
                    "mode": "shortest",
                    "origin": origin,
                    "destination": destination,
                    "distance_km": total_dist_km,
                    "walk_min": walk_min,
                    "edge_count": len(routes),
                },
            )

        elif mode == "isochrone":
            org_lng, org_lat = _parse_lnglat(origin)
            walk_speed_ms = 1.39  # 5 km/h in m/s
            distance_limit = walk_speed_ms * isochrone_minutes * 60

            src = await conn.fetchval(
                """
                SELECT id FROM routing_network_vertices_pgr
                ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
                LIMIT 1
                """, org_lng, org_lat)

            iso_edges = await conn.fetch(
                """
                SELECT node, edge, cost, agg_cost
                FROM pgr_drivingDistance(
                    'SELECT osm_id AS id, source, target, length_m AS cost FROM routing_network',
                    $1::bigint, $2::float8, directed := false
                )
                """, src, distance_limit)

            reachable_nodes = len(iso_edges)
            max_dist = round(max((r["agg_cost"] for r in iso_edges), default=0), 1)

            return RetrievalMetadata(
                hash_key=f"isochrone_{origin}_{isochrone_minutes}m_{int(time.time() * 1000)}",
                source=f"route_search(isochrone, {origin}, {isochrone_minutes}min)",
                relevance_score=1.0,
                payload={
                    "mode": "isochrone",
                    "origin": origin,
                    "isochrone_minutes": isochrone_minutes,
                    "reachable_nodes": reachable_nodes,
                    "max_distance_m": max_dist,
                },
            )

        else:
            raise ValueError(f"Unsupported route_search mode: {mode}")

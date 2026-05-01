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
# PostGIS spatial tools
# ---------------------------------------------------------------------------

def _parse_lnglat(raw: str) -> tuple[float, float]:
    """Parse 'lng,lat' string into (lng, lat) floats."""
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinate format '{raw}', expected 'lng,lat'")
    return float(parts[0]), float(parts[1])


async def _geocode(place_name: str) -> tuple[float, float]:
    """Resolve a place name to (lng, lat) via PostGIS planet_osm_point.

    Tries exact name match, then fuzzy match, then progressively truncates
    the name from the right one character at a time (e.g. "札幌駅大通" →
    "札幌駅大" → "札幌駅" → "札幌"), retrying both exact and fuzzy match
    at each step. Falls back to planet_osm_polygon (cities, regions).
    """
    pool = await get_pool()

    async def _try_point_match(name: str, fuzzy: bool = False) -> Any:
        if fuzzy:
            return await conn.fetchrow(
                """
                SELECT ST_X(ST_Transform(ST_Centroid(way), 4326)) AS lng,
                       ST_Y(ST_Transform(ST_Centroid(way), 4326)) AS lat
                FROM planet_osm_point
                WHERE name ILIKE $1
                   OR amenity ILIKE $1
                   OR tourism ILIKE $1
                   OR railway ILIKE $1
                   OR public_transport ILIKE $1
                LIMIT 1
                """,
                f"%{name}%",
            )
        return await conn.fetchrow(
            """
            SELECT ST_X(ST_Transform(way, 4326)) AS lng,
                   ST_Y(ST_Transform(way, 4326)) AS lat
            FROM planet_osm_point
            WHERE name = $1
            LIMIT 1
            """,
            name,
        )

    async def _try_polygon_match(name: str, fuzzy: bool = False) -> Any:
        if fuzzy:
            return await conn.fetchrow(
                """
                SELECT ST_X(ST_Transform(ST_Centroid(way), 4326)) AS lng,
                       ST_Y(ST_Transform(ST_Centroid(way), 4326)) AS lat
                FROM planet_osm_polygon
                WHERE name ILIKE $1
                LIMIT 1
                """,
                f"%{name}%",
            )
        return await conn.fetchrow(
            """
            SELECT ST_X(ST_Transform(ST_Centroid(way), 4326)) AS lng,
                   ST_Y(ST_Transform(ST_Centroid(way), 4326)) AS lat
            FROM planet_osm_polygon
            WHERE name = $1
            LIMIT 1
            """,
            name,
        )

    async with pool.acquire() as conn:
        row = await _try_point_match(place_name)
        if row is None:
            row = await _try_point_match(place_name, fuzzy=True)
        if row is None:
            # Progressive truncation: strip one char at a time from the right
            stripped = place_name
            while len(stripped) > 1:
                stripped = stripped[:-1]
                row = await _try_point_match(stripped)
                if row is None:
                    row = await _try_point_match(stripped, fuzzy=True)
                if row is not None:
                    break
        if row is None:
            row = await _try_polygon_match(place_name)
        if row is None:
            row = await _try_polygon_match(place_name, fuzzy=True)
        if row is None:
            raise ValueError(
                f"无法找到地点 '{place_name}' 的坐标，请尝试更具体的地名或直接提供坐标 'lng,lat'"
            )
        return float(row["lng"]), float(row["lat"])


async def _resolve_location(raw: str) -> tuple[float, float]:
    """Resolve a location string to (lng, lat).

    If the string contains a comma and both parts parse as floats, treat it as
    'lng,lat' coordinates. Otherwise geocode it as a place name via PostGIS.
    """
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass
    return await _geocode(raw)


@register_tool(
    name="spatial_search",
    description="基于地理位置检索 POI，支持空间范围过滤与类别筛选。查询半径内的餐厅、景点、住宿等。",
    parameters={
        "center": "string (中心点：支持地名如'札幌站' 或坐标 'lng,lat')",
        "radius_m": "int (搜索半径，米)",
        "category": "string (可选: restaurant/attraction/hotel/transport)",
        "limit": "int (返回条数上限，默认 10)",
    },
)
async def execute_spatial_search(task: SearchTask) -> RetrievalMetadata:
    params = task.parameters
    center = params.get("center", "")
    radius_m = int(params.get("radius_m", 1000))
    category = params.get("category")
    limit = int(params.get("limit", 10))

    lng, lat = await _resolve_location(center)
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
        "origin": "string (起点：支持地名如'札幌站' 或坐标 'lng,lat')",
        "destination": "string (可选: 终点，支持地名或坐标)",
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
            org_lng, org_lat = await _resolve_location(origin)
            dst_lng, dst_lat = await _resolve_location(destination)

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
            org_lng, org_lat = await _resolve_location(origin)
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


# ---------------------------------------------------------------------------
# Document Search — BM25 文档检索
# ---------------------------------------------------------------------------


@register_tool(
    name="document_search",
    description="在本地旅行攻略库中检索深度内容，支持按目的地地名过滤。适合查找游记、小众景点推荐、自驾路线心得等。"
               "返回相关文档的标题、片段和相关度评分。",
    parameters={
        "query": "string (搜索关键词，如'函馆夜景最佳观赏点')",
        "place_filter": "string (可选: 按地名过滤，如'函馆')",
    },
)
async def execute_document_search(task: SearchTask) -> RetrievalMetadata:
    params = task.parameters
    query = params.get("query", "")
    place_filter = params.get("place_filter")

    if not query:
        raise ValueError("document_search 缺少必填参数 'query'")

    pool = await get_pool()
    from .docs import get_document_manager
    doc_mgr = await get_document_manager(pool)

    results = doc_mgr.search(query, place_filter)

    return RetrievalMetadata(
        hash_key=f"docs_{query}_{int(time.time() * 1000)}",
        source=f"document_search(query={query}, place={place_filter})",
        relevance_score=1.0,
        payload={
            "query": query,
            "place_filter": place_filter,
            "total": len(results),
            "docs": results,
        },
    )


# ---------------------------------------------------------------------------
# Web Search — DuckDuckGo 互联网检索 + Crawler 全文抓取
# ---------------------------------------------------------------------------


@register_tool(
    name="web_search",
    description="通过 DuckDuckGo 搜索互联网并自动抓取目标网页全文。"
               "适合查找实时资讯、开放时间、门票价格、用户评价、当地活动、游记攻略等。"
               "注意：对于地理位置相关的查询（如某地附近的餐厅、景点），请优先使用 spatial_search。",
    parameters={
        "query": "string (搜索关键词，如'2024年京都红叶最佳观赏时间')",
        "max_results": "int (可选，返回结果条数上限，默认 5)",
    },
)
async def execute_web_search(task: SearchTask) -> RetrievalMetadata:
    """Execute DDG search then crawl top-3 URLs for full content."""
    import time as _time

    from .web_search import search_and_crawl

    params = task.parameters
    query = params.get("query", "")
    max_results = int(params.get("max_results", 5))

    if not query:
        raise ValueError("web_search 缺少必填参数 'query'")

    max_results = max(1, min(max_results, 20))

    payload = await search_and_crawl(query, max_results)

    return RetrievalMetadata(
        hash_key=f"web_{query}_{int(_time.time() * 1000)}",
        source=f"web_search(query={query})",
        relevance_score=1.0,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Weather Search — Open-Meteo 免费天气预报
# ---------------------------------------------------------------------------


@register_tool(
    name="weather_search",
    description="查询目的地未来天气预报（温度、降雨、风速、天气现象）。"
    "适合回答'某地未来几天的天气如何'、'何时去某地气候最佳'等问题。"
    "参数中的 location 支持中文地名（如'东京'）或坐标（'lng,lat'）。",
    parameters={
        "location": "string (地点：支持中文地名如'札幌' 或坐标 'lng,lat')",
        "days": "int (可选，预报天数 1–16，默认 7)",
    },
)
async def execute_weather_search(task: SearchTask) -> RetrievalMetadata:
    import time as _time

    from .weather import fetch_weather

    params = task.parameters
    location = params.get("location", "")

    if not location:
        raise ValueError("weather_search 缺少必填参数 'location'")

    days_raw = params.get("days", "7")
    try:
        days = int(days_raw)
    except (ValueError, TypeError):
        days = 7

    payload = await fetch_weather(location, days)

    return RetrievalMetadata(
        hash_key=f"weather_{location}_{days}_{int(_time.time() * 1000)}",
        source=f"weather_search(location={location}, days={days})",
        relevance_score=1.0,
        payload=payload,
    )

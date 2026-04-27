"""
Tool definitions and registered functions for Search node.

Tools are registered via the @register_tool decorator, which automatically
populates TOOL_METADATA (used by QueryGenerator) and TOOL_DISPATCH (used by
Search node). No manual metadata list is required.
"""

import functools
import time
from typing import Any, Dict, List

from src.agent.state import RetrievalMetadata, SearchTask
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

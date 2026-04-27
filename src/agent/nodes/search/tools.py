"""
Tool definitions and registered functions for Search node.

These tools are the concrete implementations available for executing SearchTask.
For each tool, we register:
- A function that performs the task (current implementations are placeholders / minimal examples)
- A metadata dict describing name, description, and parameter schema.

The metadata list can be injected directly into QueryGenerator's prompt to inform
the LLM which tools are available and how to call them.
"""

import time
from typing import Any, Dict, List, Optional

from src.agent.state import RetrievalMetadata, SearchTask
from src.utils.logger import get_logger

logger = get_logger("SearchTools")

# ---------------------------------------------------------------------------
# Registered tool implementations (mock outputs)
# ---------------------------------------------------------------------------

async def execute_web_search(task: SearchTask) -> RetrievalMetadata:
    """
    Mock implementation of web search.
    Returns a placeholder RetrievalMetadata.
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


async def execute_vector_search(task: SearchTask) -> RetrievalMetadata:
    """
    Mock implementation of vector database search.
    Returns a placeholder RetrievalMetadata.
    """
    params = task.parameters
    query = params.get("query", "mock query")
    collection = params.get("collection", "default")

    logger.info(f"Mock vector search for: {query} (collection={collection})")

    hash_key = f"mock_vec_{query}_{int(time.time() * 1000)}"
    return RetrievalMetadata(
        hash_key=hash_key,
        source=f"vector_db/{collection}: {query}",
        relevance_score=0.9,
    )


# ---------------------------------------------------------------------------
# Additional tool stubs (declared but not yet implemented)
# ---------------------------------------------------------------------------

async def execute_flight_search(task: SearchTask) -> RetrievalMetadata:
    """
    Placeholder for flight API search.
    To be implemented when flight data source is available.
    """
    raise NotImplementedError("Flight search is not yet implemented.")


async def execute_hotel_search(task: SearchTask) -> RetrievalMetadata:
    """
    Placeholder for hotel database search.
    To be implemented when accommodation data source is available.
    """
    raise NotImplementedError("Hotel search is not yet implemented.")


# ---------------------------------------------------------------------------
# Tool metadata for prompt injection
# ---------------------------------------------------------------------------

TOOL_METADATA: List[Dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "搜索互联网获取最新旅游信息、攻略、评价等。",
        "parameters": {
            "query": "string (搜索关键词)"
        },
    },
    {
        "name": "vector_db",
        "description": "查询本地旅游知识库，获取结构化的景点、餐厅、酒店底表信息。",
        "parameters": {
            "query": "string (检索指令)",
            "collection": "string (可选: attractions, restaurants, hotels)"
        },
    },
    {
        "name": "flight_api",
        "description": "查询实时航班信息、票价（尚未实现）。",
        "parameters": {
            "origin": "string (出发地代码/名称)",
            "destination": "string (目的地代码/名称)",
            "date": "string (出发日期)"
        },
    },
    {
        "name": "hotel_api",
        "description": "查询酒店可用性、价格（尚未实现）。",
        "parameters": {
            "destination": "string (目的地)",
            "check_in": "string (入住日期)",
            "check_out": "string (退房日期)",
            "guests": "int (入住人数)"
        },
    },
]

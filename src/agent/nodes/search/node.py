"""
Module: src.agent.nodes.search.node
Responsibility: Executes search tasks from ResearchManifest using registered tool handlers.
Parent Module: src.agent.nodes.search
Dependencies: src.agent.state, src.utils.logger, src.agent.nodes.search.tools
"""

import time
from typing import Any, Dict, List

from src.agent.nodes.search import tools
from src.agent.nodes.utils import build_trace
from src.agent.state import ResearchManifest, RetrievalMetadata, SearchTask
from src.utils.logger import get_logger

logger = get_logger("SearchNode")


async def _execute_tasks(tasks: List[SearchTask]) -> tuple[List[RetrievalMetadata], bool]:
    results: List[RetrievalMetadata] = []
    has_errors = False

    for idx, task in enumerate(tasks):
        handler = tools.TOOL_DISPATCH.get(task.tool_name)
        if handler is None:
            logger.error(f"Unsupported tool '{task.tool_name}' in task {idx}.")
            has_errors = True
            continue

        try:
            results.append(await handler(task))
        except Exception as e:
            logger.error(f"Failed to execute tool '{task.tool_name}' for task {idx}: {e}", exc_info=True)
            has_errors = True
            results.append(
                RetrievalMetadata(
                    hash_key=f"error_{task.tool_name}_{idx}",
                    source="execution_error",
                    relevance_score=0.0,
                )
            )

    return results, has_errors


async def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search Execution Node.
    Reads active queries from ResearchManifest, executes tools without LLM,
    and appends verified results to the manifest.
    """
    start_time = time.time()
    logger.info("Executing search tasks at [SearchNode]...")

    research_data: ResearchManifest = state.get("research_data")

    if not research_data:
        logger.warning("No research_data found, skipping search.")
        trace = build_trace("search", "SKIPPED", int((time.time() - start_time) * 1000), {"reason": "research_data missing"})
        return {"trace_history": [trace]}

    tasks: List[SearchTask] = research_data.active_queries
    if not tasks:
        logger.info("No active queries present.")
        trace = build_trace("search", "SUCCESS", int((time.time() - start_time) * 1000), {"task_count": 0})
        return {
            "research_data": research_data,
            "trace_history": [trace],
        }

    results, has_errors = await _execute_tasks(tasks)

    updated_manifest = ResearchManifest(
        active_queries=[],
        verified_results=research_data.verified_results + results,
        feedback_history=research_data.feedback_history,
        research_history=research_data.research_history,
    )

    latency_ms = int((time.time() - start_time) * 1000)
    status = "FAIL" if has_errors else "SUCCESS"
    trace = build_trace(
        "search",
        status,
        latency_ms,
        {"executed_tasks": len(tasks), "collected_results": len(results)},
    )

    logger.info(f"Search execution completed with status: {status}")
    return {
        "research_data": updated_manifest,
        "trace_history": [trace],
    }

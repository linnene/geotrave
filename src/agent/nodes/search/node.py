import time
from typing import Dict, Any, List

from src.agent.state import TraceLog, ResearchManifest, SearchTask, RetrievalMetadata
from src.utils.logger import get_logger
from src.agent.nodes.search import tools  # <-- 工具函数与元数据在此

logger = get_logger("SearchNode")


async def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search Execution Node.
    Reads active queries from ResearchManifest, executes tools without LLM,
    and appends verified results to the manifest.
    """
    start_time = time.time()
    logger.info("Executing search tasks at [SearchNode]...")

    research_data: ResearchManifest = state.get("research_data")
    trace_history: list = state.get("trace_history", [])

    if not research_data:
        logger.warning("No research_data found, skipping search.")
        trace = TraceLog(
            node="search",
            status="SKIPPED",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"reason": "research_data missing"},
        )
        return {"trace_history": trace_history + [trace]}

    tasks: List[SearchTask] = research_data.active_queries
    if not tasks:
        logger.info("No active queries present.")
        trace = TraceLog(
            node="search",
            status="SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"task_count": 0},
        )
        return {
            "research_data": research_data,
            "trace_history": trace_history + [trace],
        }

    # Tool dispatcher (uses the automatically built dispatch map)
    tool_dispatcher = tools.TOOL_DISPATCH

    new_results: List[RetrievalMetadata] = []
    error_occurred = False

    for idx, task in enumerate(tasks):
        tool_name = task.tool_name
        handler = tool_dispatcher.get(tool_name)
        if handler is None:
            logger.error(f"Unsupported tool '{tool_name}' in task {idx}.")
            error_occurred = True
            continue

        try:
            result_meta = await handler(task)
            new_results.append(result_meta)
        except Exception as e:
            logger.error(
                f"Failed to execute tool '{tool_name}' for task {idx}: {e}",
                exc_info=True,
            )
            error_occurred = True
            # Append an error entry so that the loop still has one item per task
            new_results.append(
                RetrievalMetadata(
                    hash_key=f"error_{tool_name}_{idx}",
                    source="execution_error",
                    relevance_score=0.0,
                )
            )

    # Update research manifest: clear active queries, append new results
    updated_manifest = ResearchManifest(
        active_queries=[],
        verified_results=research_data.verified_results + new_results,
        feedback_history=research_data.feedback_history,
    )

    latency_ms = int((time.time() - start_time) * 1000)
    status = "FAIL" if error_occurred else "SUCCESS"
    trace = TraceLog(
        node="search",
        status=status,
        latency_ms=latency_ms,
        detail={
            "executed_tasks": len(tasks),
            "collected_results": len(new_results),
        },
    )

    logger.info(f"Search execution completed with status: {status}")
    return {
        "research_data": updated_manifest,
        "trace_history": trace_history + [trace],
    }

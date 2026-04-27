import time
from typing import Dict, Any, List

from src.agent.state import TraceLog, ResearchManifest, SearchTask, RetrievalMetadata
from src.utils.logger import get_logger
from src.crawler.fetcher import ContentFetcher
from src.database.vector_db.service import search_similar_documents

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

    # Tool dispatcher (no LLM involved)
    tool_dispatcher = {
        "web_search": _execute_web_search,
        "vector_db": _execute_vector_search,
    }

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


async def _execute_web_search(task: SearchTask) -> RetrievalMetadata:
    """
    Executes a web search via ContentFetcher.
    """
    params = task.parameters
    query = params.get("query", "")
    fetcher = ContentFetcher()

    # Placeholder: use a generic search URL; in production this should interface
    # with a real search API.
    url = f"https://www.google.com/search?q={query}"
    html = await fetcher.fetch_fast(url)

    if html is None:
        raise RuntimeError(f"Web search for '{query}' returned no content.")

    hash_key = f"web_{query}_{int(time.time() * 1000)}"
    return RetrievalMetadata(
        hash_key=hash_key,
        source=f"web_search: {query}",
        relevance_score=0.8,  # placeholder score
    )


async def _execute_vector_search(task: SearchTask) -> RetrievalMetadata:
    """
    Queries the local knowledge base via vector search.
    """
    params = task.parameters
    query = params.get("query", "")
    collection = params.get("collection", "default")

    results = await search_similar_documents(query, k=3)

    if not results:
        return RetrievalMetadata(
            hash_key=f"vec_empty_{query}_{int(time.time() * 1000)}",
            source=f"vector_db/{collection}",
            relevance_score=0.0,
        )

    # Take the first result's metadata to generate a RetrievalMetadata entry.
    first = results[0]
    if isinstance(first, (list, tuple)) and len(first) >= 2:
        doc_text, meta = first[0], first[1]
    else:
        doc_text, meta = str(first), {}

    hash_key = meta.get("hash", f"vec_{query}_{int(time.time() * 1000)}")
    return RetrievalMetadata(
        hash_key=hash_key,
        source=f"vector_db/{collection}: {query}",
        relevance_score=0.9,  # placeholder score
    )

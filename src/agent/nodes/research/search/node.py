"""
Module: src.agent.nodes.search.node
Responsibility: Executes search tasks from ResearchManifest, wraps results in
                ResearchResult envelope, writes to subgraph-internal loop_state.
Parent Module: src.agent.nodes.search
Dependencies: src.agent.state, src.agent.state.schema, src.agent.nodes.search.tools
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import tools
from src.agent.nodes.utils import build_trace
from src.agent.state import ResearchManifest, SearchTask
from src.agent.state.schema import ResearchResult
from src.utils.logger import get_logger

logger = get_logger("SearchNode")


def _generate_summary(payload: Dict[str, Any]) -> str:
    """从 payload 生成 ≤500 字符的摘要，供 Critic LLM 评分使用。

    JSON 型结果: 提取前 5 条记录的 name / category 等关键字段。
    后续扩展 text / html / url_list 类型。
    """
    # POI 列表型
    pois = payload.get("pois")
    if pois and isinstance(pois, list):
        names = [p.get("name", "?") for p in pois[:5]]
        summary = f"POI: {', '.join(names)}"
        if len(pois) > 5:
            summary += f" ... 共{len(pois)}条"
        return summary[:500]

    # 路线型
    if payload.get("mode") in ("shortest", "isochrone"):
        mode = payload["mode"]
        if mode == "shortest":
            summary = (
                f"路线: {payload.get('origin')}→{payload.get('destination')}, "
                f"{payload.get('distance_km')}km, 步行约{payload.get('walk_min')}分"
            )
        else:
            summary = (
                f"等时圈: {payload.get('origin')} {payload.get('isochrone_minutes')}分, "
                f"可达节点{payload.get('reachable_nodes')}, 最大距离{payload.get('max_distance_m')}m"
            )
        return summary[:500]

    # 通用 fallback: 序列化前 500 字符
    raw = json.dumps(payload, ensure_ascii=False)
    return raw[:500]


async def _execute_tasks(
    tasks: List[SearchTask],
) -> Dict[str, ResearchResult]:
    """执行全部 SearchTask，将结果包裹为 ResearchResult envelope。

    每个任务由对应注册 handler 执行，原始 RetrievalMetadata.payload
    作为 content 填入 envelope，同时生成 content_summary。

    Returns:
        {query_text: ResearchResult} 映射。
    """
    results: Dict[str, ResearchResult] = {}

    for idx, task in enumerate(tasks):
        handler = tools.TOOL_DISPATCH.get(task.tool_name)
        if handler is None:
            logger.error(f"Unsupported tool '{task.tool_name}' in task {idx}.")
            continue

        query_text = json.dumps(task.parameters, ensure_ascii=False)
        try:
            raw = await handler(task)
            envelope = ResearchResult(
                tool_name=task.tool_name,
                query=query_text,
                content_type="json",
                content=raw.payload,
                content_summary=_generate_summary(raw.payload),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            results[query_text] = envelope
        except Exception as e:
            logger.error(
                f"Failed to execute tool '{task.tool_name}' for task {idx}: {e}",
                exc_info=True,
            )
            # 错误结果同样用 envelope 包裹，供 Critic 过滤
            error_env = ResearchResult(
                tool_name=task.tool_name,
                query=query_text,
                content_type="json",
                content={"error": str(e)},
                content_summary=f"执行失败: {str(e)[:500]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            results[query_text] = error_env

    return results


async def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Search 执行节点（无 LLM）。

    1. 读取 research_data.loop_state.active_queries
    2. 并行/顺序执行工具，包裹为 ResearchResult envelope
    3. 写入 research_data.loop_state.query_results，清空 active_queries
    """
    start_time = time.time()
    logger.info("Executing search tasks at [SearchNode]...")

    research_data: ResearchManifest = state.get("research_data")

    if not research_data:
        logger.warning("No research_data found, skipping search.")
        trace = build_trace(
            "search", "SKIPPED",
            int((time.time() - start_time) * 1000),
            {"reason": "research_data missing"},
        )
        return {"trace_history": [trace]}

    tasks: List[SearchTask] = research_data.loop_state.active_queries
    if not tasks:
        logger.info("No active queries present.")
        trace = build_trace(
            "search", "SUCCESS",
            int((time.time() - start_time) * 1000),
            {"task_count": 0},
        )
        return {
            "research_data": research_data,
            "trace_history": [trace],
        }

    query_results = await _execute_tasks(tasks)

    # 写入子图内部 State (loop_state.query_results)，同时清空 active_queries
    new_research_data = research_data.model_copy(
        update={
            "loop_state": research_data.loop_state.model_copy(
                update={
                    "query_results": query_results,
                    "active_queries": [],
                }
            ),
        }
    )

    latency_ms = int((time.time() - start_time) * 1000)
    trace = build_trace(
        "search",
        "SUCCESS",
        latency_ms,
        {
            "executed_tasks": len(tasks),
            "collected_results": len(query_results),
        },
    )

    logger.info(
        f"Search done: {len(tasks)} tasks → {len(query_results)} envelopes"
    )
    return {
        "research_data": new_research_data,
        "trace_history": [trace],
    }

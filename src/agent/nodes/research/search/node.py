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
    """从 payload 生成 ≤500 字符的摘要，供 Critic LLM 评分使用。"""

    # 单条网页搜索结果（拆分后独立的 web_search 结果）
    if "url" in payload and "title" in payload and "query" not in payload:
        title = payload.get("title", "?")
        snippet = payload.get("snippet", "")[:200]
        content_len = len(payload.get("content") or "")
        status = payload.get("crawl_status", "?")
        summary = f"[web] {title}"
        if snippet:
            summary += f" | 摘要: {snippet}"
        if content_len:
            summary += f" | 全文{content_len}字"
        summary += f" | 抓取: {status}"
        return summary[:500]

    # POI 列表型
    pois = payload.get("pois")
    if pois and isinstance(pois, list):
        names = [p.get("name") or "?" for p in pois[:5]]
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

    对于 web_search：每个独立搜索结果（URL）拆分为单独的 ResearchResult，
    键为 {query_text}#{idx}，使得 Critic 可逐条评分、Hash 可逐条存储。
    其他工具保持原有的一 task 一 result 行为。

    Returns:
        {query_text or query_text#idx: ResearchResult} 映射。
    """
    results: Dict[str, ResearchResult] = {}

    for idx, task in enumerate(tasks):
        query_text = json.dumps(task.parameters, ensure_ascii=False)
        handler = tools.TOOL_DISPATCH.get(task.tool_name)
        if handler is None:
            logger.error(f"Unsupported tool '{task.tool_name}' in task {idx}.")
            results[query_text] = ResearchResult(
                tool_name=task.tool_name,
                query=query_text,
                content_type="json",
                content={"error": f"Unknown tool: {task.tool_name}"},
                content_summary=f"错误: 未知工具 {task.tool_name}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            continue
        try:
            raw = await handler(task)

            # web_search：每个独立结果拆分为单独的 ResearchResult
            if task.tool_name == "web_search":
                result_items = raw.payload.get("results", [])
                if result_items:
                    for ri, item in enumerate(result_items):
                        item_key = f"{query_text}#{ri}"
                        results[item_key] = ResearchResult(
                            tool_name=task.tool_name,
                            query=item_key,
                            content_type="json",
                            content=item,
                            content_summary=_generate_summary(item),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                else:
                    # 无结果也保留一条空 envelope，供 Critic 识别
                    results[query_text] = ResearchResult(
                        tool_name=task.tool_name,
                        query=query_text,
                        content_type="json",
                        content={"query": raw.payload.get("query", ""), "total": 0, "results": []},
                        content_summary=f"web_search: 无结果 (query={raw.payload.get('query', '?')})",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
            else:
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


def _is_error_result(rr: ResearchResult) -> bool:
    """检查 ResearchResult 是否为错误 envelope（应被 Critic 前的 L0 过滤器拦截）。"""
    return isinstance(rr.content, dict) and "error" in rr.content


async def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Search 执行节点（无 LLM）。

    1. 读取 research_data.loop_state.active_queries
    2. 执行工具，包裹为 ResearchResult envelope
    3. 分流：文档结果 → passed_doc_ids（跳过 Critic）；非文档 → query_results
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

    # --- 分流：文档结果 vs 非文档结果 ---
    doc_results = {k: v for k, v in query_results.items() if v.tool_name == "document_search"}
    non_doc_results = {k: v for k, v in query_results.items() if v.tool_name != "document_search"}

    # --- L0 错误过滤器：错误 envelope 不入 Critic，避免污染评分 ---
    error_results = {k: v for k, v in non_doc_results.items() if _is_error_result(v)}
    clean_non_doc = {k: v for k, v in non_doc_results.items() if not _is_error_result(v)}
    if error_results:
        logger.warning(
            "L0 filter: %d error result(s) excluded from Critic: %s",
            len(error_results),
            [(k, v.content.get("error", "")[:80]) for k, v in error_results.items()],
        )

    # 文档结果：提取 doc_ids，累积到 passed_doc_ids（不进入 Critic）
    new_doc_ids: list = []
    for rr in doc_results.values():
        docs = rr.content.get("docs", []) if isinstance(rr.content, dict) else []
        for d in docs:
            did = d.get("doc_id") if isinstance(d, dict) else None
            if did and did not in new_doc_ids:
                new_doc_ids.append(did)

    previous_doc_ids = list(research_data.loop_state.passed_doc_ids)
    merged_doc_ids = previous_doc_ids + [d for d in new_doc_ids if d not in previous_doc_ids]

    # 更新 loop_state：query_results 只含非文档且非错误的结果
    new_loop_state = research_data.loop_state.model_copy(
        update={
            "query_results": clean_non_doc,
            "active_queries": [],
            "passed_doc_ids": merged_doc_ids,
        }
    )

    new_research_data = research_data.model_copy(
        update={"loop_state": new_loop_state}
    )

    latency_ms = int((time.time() - start_time) * 1000)
    trace = build_trace(
        "search",
        "SUCCESS",
        latency_ms,
        {
            "executed_tasks": len(tasks),
            "collected_results": len(query_results),
            "doc_results": len(doc_results),
            "doc_ids_added": len(new_doc_ids),
            "error_results_filtered": len(error_results),
        },
    )

    logger.info(
        f"Search done: {len(tasks)} tasks → {len(clean_non_doc)} non-doc + {len(doc_results)} doc"
        f" (+ {len(error_results)} errors filtered)"
    )
    return {
        "research_data": new_research_data,
        "trace_history": [trace],
    }

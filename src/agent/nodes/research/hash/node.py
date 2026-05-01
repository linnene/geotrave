"""
Module: src.agent.nodes.research.hash
Responsibility: Hash node — persist passed results to Retrieval DB and expose
                minimal {query: [hash_key, ...]} mapping to parent graph.
Parent Module: src.agent.nodes.research
Dependencies: hashlib, src.agent.state, src.database.retrieval_db
"""

import hashlib
import json
import time
from collections import defaultdict
from typing import Any, Dict, List

from src.agent.state import TravelState
from src.agent.state.schema import (
    CriticResult,
    ExecutionSigns,
    ResearchLoopInternal,
)
from src.database.retrieval_db import batch_store_results
from src.agent.nodes.utils.history_tools import build_trace
from src.utils.logger import get_logger

logger = get_logger("HashNode")


def generate_hash_key(query: str, content: Any) -> str:
    """生成内容寻址 hash key。

    基于 query + 规范化 JSON 内容的 SHA256，相同 query 和内容产生相同 hash，用于去重。
    使用完整序列化内容而非截断，避免 JSON 键名前缀碰撞。
    """
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    fingerprint = f"{query}|{serialized}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


async def persist_results(
    all_passed_results: List[CriticResult],
    query_results: Dict[str, Any],
    session_id: str,
) -> Dict[str, List[str]]:
    """持久化通过过滤的结果到 Retrieval DB。

    对每条 CriticResult 生成 hash_key，合并原始 ResearchResult.content 后批量写入
    PostgreSQL JSONB，返回 {query: [hash_key, ...]} 映射供父图暴露。

    Args:
        all_passed_results: Critic 通过的全部结果。
        query_results: Search 节点产出的 {query: ResearchResult} 映射。
        session_id: 当前会话 ID（对应 LangGraph thread_id）。

    Returns:
        {query_text: [hash_key, ...]} 映射。
    """
    if not all_passed_results:
        logger.info("Hash: no results to persist")
        return {}

    mapping: Dict[str, List[str]] = defaultdict(list)
    records: List[Dict[str, Any]] = []

    for r in all_passed_results:
        # 合并 CriticResult 元数据 + 原始 ResearchResult.content
        payload = r.model_dump()
        raw = query_results.get(r.query)
        if raw is not None:
            raw_content = raw.get("content") if isinstance(raw, dict) else getattr(raw, "content", None)
            payload["_research_content"] = raw_content
        hk = generate_hash_key(r.query, payload)
        mapping[r.query].append(hk)
        records.append({
            "hash_key": hk,
            "payload": payload,
        })

    try:
        await batch_store_results(records, session_id)
        logger.info(f"Hash: persisted {len(records)} results for session={session_id}")
    except Exception as e:
        logger.error("Hash: batch_store_results failed: %s", e)
        mapping.clear()
        for r in all_passed_results:
            mapping[r.query].append("")  # placeholder to preserve query coverage info
    return dict(mapping)


async def hash_node(state: TravelState) -> Dict[str, Any]:
    """Hash 节点 — 持久化 + 全局状态最小暴露。

    流程:
    1. 读取 loop_state.all_passed_results（Critic 累计通过的结果）
    2. 生成 hash_key 并写入 Retrieval DB
    3. 将 {query: [hash_key, ...]} 写入 research_data.research_hashes
    4. 设置 execution_signs.is_loop_exit = True，通知父图子图已退出
    """
    start_time = time.time()
    logger.info("Hash: starting persistence")

    research_data = state.get("research_data")
    loop_state: ResearchLoopInternal = research_data.loop_state
    all_passed = loop_state.all_passed_results

    # 合并文档 ID：从 loop_state.passed_doc_ids 提升到 Manifest.matched_doc_ids
    # （无论是否有非文档结果通过，文档 ID 都必须提升，否则会丢失文档检索结果）
    existing_doc_ids = list(research_data.matched_doc_ids)
    new_doc_ids = list(loop_state.passed_doc_ids)
    merged_doc_ids = existing_doc_ids + [d for d in new_doc_ids if d not in existing_doc_ids]

    if not all_passed:
        logger.info("Hash: no passed results, skipping persistence")
        # 仍有文档 ID 需要提升
        if merged_doc_ids != existing_doc_ids:
            new_research_data = research_data.model_copy(
                update={"matched_doc_ids": merged_doc_ids}
            )
            trace = build_trace(
                "hash",
                "SKIPPED",
                latency_ms=int((time.time() - start_time) * 1000),
                detail={"reason": "all_passed_results 为空", "matched_docs": len(merged_doc_ids)},
            )
            return {
                "research_data": new_research_data,
                "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(update={"is_loop_exit": True}),
                "trace_history": [trace],
            }
        trace = build_trace(
            "hash",
            "SKIPPED",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"reason": "all_passed_results 为空"},
        )
        return {
            "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(update={"is_loop_exit": True}),
            "trace_history": [trace],
        }

    # 从 LangGraph checkpoint 的 thread_id 获取 session_id
    # hash_node 由子图调用，父图的 config 会透传 thread_id
    # 这里使用一个基于消息 ID 的 fallback
    messages = state.get("messages", [])
    session_id = messages[0].id if messages else "unknown"

    # 持久化至 Retrieval DB（附带原始 ResearchResult.content）
    research_hashes = await persist_results(all_passed, loop_state.query_results, session_id)

    # 合并已有的 research_hashes（跨多轮调研累积）
    existing_hashes = dict(research_data.research_hashes)
    for query, hashes in research_hashes.items():
        if query in existing_hashes:
            existing_hashes[query] = existing_hashes[query] + [
                h for h in hashes if h not in existing_hashes[query]
            ]
        else:
            existing_hashes[query] = hashes

    new_research_data = research_data.model_copy(
        update={
            "research_hashes": existing_hashes,
            "matched_doc_ids": merged_doc_ids,
        }
    )

    trace = build_trace(
        "hash",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "persisted_count": len(all_passed),
            "hash_groups": len(research_hashes),
            "session_id": session_id,
        },
    )

    logger.info(
        f"Hash done: persisted {len(all_passed)} results, "
        f"{len(research_hashes)} query groups, "
        f"{len(merged_doc_ids)} matched docs"
    )

    return {
        "research_data": new_research_data,
        "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(update={"is_loop_exit": True}),
        "trace_history": [trace],
    }

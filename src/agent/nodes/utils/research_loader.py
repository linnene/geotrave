"""
Module: src.agent.nodes.utils.research_loader
Responsibility: Fetch and format research content from Retrieval DB for prompt injection.
               Used by Recommender and Planner to access actual search results,
               not just CriticResult scores.

Parent Module: src.agent.nodes.utils
Dependencies: src.database.retrieval_db, src.agent.state.schema
"""

import json
from typing import Any, Dict, List, Optional

from src.agent.state.schema import ResearchManifest
from src.utils.logger import get_logger

logger = get_logger("ResearchLoader")

MAX_CONTENT_ITEMS = 20          # Number of top results included in prompt
MAX_CONTENT_LENGTH_PER_ITEM = 800  # Characters per result entry


async def fetch_research_content(manifest: Optional[ResearchManifest]) -> str:
    """从 Retrieval DB 拉取真实检索内容，格式化为可注入 prompt 的文本。

    当 manifest 为 None 或无 research_hashes 时返回空占位字符串。
    DB 不可用时 fallback 到 CriticResult rationale（降级摘要）。
    """
    if manifest is None:
        return "暂无研究数据"

    research_hashes = manifest.research_hashes
    if not research_hashes:
        return "当前无通过评估的研究结果"

    # 收集中所有 hash_keys
    all_hash_keys: List[str] = []
    for hashes in research_hashes.values():
        all_hash_keys.extend(hashes)

    if not all_hash_keys:
        return "当前无通过评估的研究结果（hash key 为空）"

    # 查询 Retrieval DB
    try:
        from src.database.retrieval_db import get_results

        records: Dict[str, Dict[str, Any]] = await get_results(all_hash_keys)
    except Exception as exc:
        logger.warning("Failed to query Retrieval DB: %s — falling back to CriticResult rationales", exc)
        return _fallback_rationale(manifest)

    if not records:
        return _fallback_rationale(manifest)

    # 格式化为 prompt 可用文本
    lines: List[str] = []
    count = 0
    for hk, payload in records.items():
        if count >= MAX_CONTENT_ITEMS:
            break
        entry = _format_entry(hk, payload)
        if entry:
            lines.append(entry)
            count += 1

    if not lines:
        return _fallback_rationale(manifest)

    logger.info("ResearchLoader: loaded %d research entries for prompt", count)
    return "\n\n".join(lines)


def _format_entry(_hk: str, payload: Dict[str, Any]) -> Optional[str]:
    """将单条 payload 格式化为 prompt 友好的文本。"""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Skipping non-JSON string payload for hash=%s", _hk[:16])
            return None
    tool_name = payload.get("tool_name", "unknown")
    query = payload.get("query", "")
    rationale = payload.get("rationale", "")
    relevance = payload.get("relevance_score", 0)
    utility = payload.get("utility_score", 0)
    raw_content = payload.get("_research_content")

    parts: List[str] = []

    # 名称/标题
    name = payload.get("name") or (raw_content.get("name") if isinstance(raw_content, dict) else None)
    if name:
        parts.append(f"**{name}**")

    # 类型/维度标签
    type_tag = (
        payload.get("content_type")
        or (raw_content.get("type") if isinstance(raw_content, dict) else None)
        or tool_name
    )
    parts.append(f"[{type_tag}] {query[:120]}")
    parts.append(f"评分: 相关性={relevance:.0f} 有效性={utility:.0f}")

    if rationale:
        parts.append(f"摘要: {rationale[:200]}")

    # 结构化字段抽取
    if isinstance(raw_content, list):
        # POI 列表: 提取前 5 条的名称和关键信息
        poi_lines = []
        for poi in raw_content[:5]:
            if isinstance(poi, dict):
                poi_name = poi.get("name") or poi.get("title") or ""
                poi_cat = poi.get("category") or poi.get("type") or ""
                poi_addr = poi.get("address") or poi.get("location") or ""
                extra = f" ({poi_cat})" if poi_cat else ""
                if poi_addr:
                    extra += f" @ {poi_addr}"
                poi_lines.append(f"  - {poi_name}{extra}")
        if poi_lines:
            parts.append("数据条目:")
            parts.extend(poi_lines)
            if len(raw_content) > 5:
                parts.append(f"  ... 共 {len(raw_content)} 条")
    elif isinstance(raw_content, dict):
        content_str = json.dumps(raw_content, ensure_ascii=False)
        if len(content_str) <= MAX_CONTENT_LENGTH_PER_ITEM:
            parts.append(f"数据: {content_str}")
        else:
            parts.append(f"数据: {content_str[:MAX_CONTENT_LENGTH_PER_ITEM]}...")
    elif isinstance(raw_content, str):
        parts.append(f"内容: {raw_content[:MAX_CONTENT_LENGTH_PER_ITEM]}")

    return "\n".join(parts)


def _fallback_rationale(manifest: ResearchManifest) -> str:
    """DB 不可用时的降级方案：从 loop_state 提取 CriticResult rationale。"""
    loop_state = manifest.loop_state
    passed = loop_state.all_passed_results if loop_state else []

    if not passed:
        return "暂无可用研究数据"

    lines = ["[降级摘要 — Retrieval DB 不可用]"]
    for cr in passed[:MAX_CONTENT_ITEMS]:
        lines.append(
            f"- [{cr.tool_name}] {cr.query[:120]} "
            f"(relevance={cr.relevance_score:.0f}): {cr.rationale[:200]}"
        )
    return "\n".join(lines)

"""
Module: src.agent.nodes.research.critic
Responsibility: Critic node — 3-layer quality filter for Research Loop results.
Parent Module: src.agent.nodes.research
Dependencies: yaml, src.agent.state, src.utils, src.agent.nodes.utils

Layer 1: blacklist keyword filter (code, O(1) per result)
Layer 2: LLM scoring (safety_tag + relevance + utility per batch)
Layer 3: threshold filter (code, drops unsafe or score < MIN_SCORE_THRESHOLD)
"""

import json
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.agent.state import TravelState
from src.agent.state.schema import (
    CriticResult,
    LoopSummary,
    ResearchLoopInternal,
    ResearchResult,
)
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import critic_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils.history_tools import build_trace
from .config import (
    CRITIC_BATCH_SIZE,
    CRITIC_TEMPERATURE,
    MAX_LOOPS,
    MAX_TOKENS,
    MIN_SCORE_THRESHOLD,
    PASS_COUNT_MIN,
)

logger = get_logger("CriticNode")

_BLACKLIST_PATH = Path(__file__).resolve().parent / "blacklist.yaml"


# =============================================================================
# Layer 1 — 黑名单关键词过滤
# =============================================================================


def load_blacklist() -> List[str]:
    """从 blacklist.yaml 加载关键词列表。"""
    with open(_BLACKLIST_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("keywords", [])


def blacklist_filter(
    results: Dict[str, ResearchResult], blacklist: List[str]
) -> Tuple[Dict[str, ResearchResult], Dict[str, str]]:
    """Layer 1 过滤。

    检查每条结果的 content_summary 是否命中黑名单关键词。

    Args:
        results: {query_text: ResearchResult} 映射。
        blacklist: 黑名单关键词列表。

    Returns:
        (passed, rejected) — passed 保持 {query: ResearchResult};
        rejected 为 {query: reason}。
    """
    passed: Dict[str, ResearchResult] = {}
    rejected: Dict[str, str] = {}

    for query_text, result in results.items():
        summary_lower = result.content_summary.lower()
        hit = False
        for keyword in blacklist:
            if keyword.lower() in summary_lower:
                rejected[query_text] = f"blacklist hit: {keyword}"
                hit = True
                break
        if not hit:
            passed[query_text] = result

    logger.info(f"Layer 1 (blacklist): passed={len(passed)}, rejected={len(rejected)}")
    return passed, rejected


# =============================================================================
# Layer 2 — LLM 评分
# =============================================================================


def _get_critic_format_instructions() -> str:
    """构建 Critic LLM 输出格式说明（包含 results 数组 + 循环决策字段）。"""
    item_schema = CriticResult.model_json_schema()
    wrapper_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": item_schema,
                "description": "每条结果的评估列表",
            },
            "continue_loop": {
                "type": "boolean",
                "description": "当前结果是否已充分覆盖查询意图，false 表示可以退出循环",
            },
            "feedback": {
                "type": "string",
                "description": "如 continue_loop=true，说明下一步搜索方向",
            },
        },
        "required": ["results", "continue_loop", "feedback"],
    }
    return json.dumps(wrapper_schema, indent=2, ensure_ascii=False)


def _build_batch_json(batch: Dict[str, ResearchResult]) -> str:
    """将一批结果组装为 Critic LLM 输入 JSON。"""
    items = []
    for query_text, result in batch.items():
        items.append({
            "query": query_text,
            "tool_name": result.tool_name,
            "content_type": result.content_type,
            "content_summary": result.content_summary,
        })
    return json.dumps(items, indent=2, ensure_ascii=False)


async def llm_score_batch(
    batch: Dict[str, ResearchResult],
) -> Tuple[List[CriticResult], bool, str]:
    """Layer 2: 将一批结果送 Critic LLM 评分。

    Args:
        batch: {query_text: ResearchResult}，最多 CRITIC_BATCH_SIZE 条。

    Returns:
        (results, continue_loop, feedback)
    """
    format_instructions = _get_critic_format_instructions()
    results_json = _build_batch_json(batch)

    prompt_str = critic_prompt_template.format(
        results_json=results_json,
        format_instructions=format_instructions,
    )

    llm = LLMFactory.get_model(
        "Critic", temperature=CRITIC_TEMPERATURE, max_tokens=MAX_TOKENS
    )
    bound_llm = llm.bind(response_format={"type": "json_object"})

    raw_result = await bound_llm.ainvoke(prompt_str)

    content = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
    if isinstance(content, list):
        content_str = "".join(
            t.get("text", "") if isinstance(t, dict) else str(t) for t in content
        )
    else:
        content_str = str(content)

    parsed = json.loads(content_str)

    results = [CriticResult(**item) for item in parsed.get("results", [])]
    continue_loop = parsed.get("continue_loop", True)
    feedback = parsed.get("feedback", "")

    logger.info(
        f"Layer 2 (LLM): scored={len(results)}, continue_loop={continue_loop}"
    )
    return results, continue_loop, feedback


# =============================================================================
# Layer 3 — 分数阈值过滤（纯代码）
# =============================================================================


def code_filter(
    critic_results: List[CriticResult],
) -> Tuple[List[CriticResult], List[CriticResult]]:
    """Layer 3 过滤。

    丢弃规则:
    1. safety_tag == "unsafe"
    2. relevance_score < MIN_SCORE_THRESHOLD
    3. utility_score < MIN_SCORE_THRESHOLD

    Returns:
        (passed, rejected)
    """
    passed: List[CriticResult] = []
    rejected: List[CriticResult] = []

    for r in critic_results:
        if r.safety_tag == "unsafe":
            rejected.append(r)
        elif r.relevance_score < MIN_SCORE_THRESHOLD or r.utility_score < MIN_SCORE_THRESHOLD:
            rejected.append(r)
        else:
            passed.append(r)

    logger.info(f"Layer 3 (code): passed={len(passed)}, rejected={len(rejected)}")
    return passed, rejected


# =============================================================================
# 循环退出决策（混合判断）
# =============================================================================


def should_continue_loop(
    pass_count: int,
    llm_continue_loop: bool,
    loop_iter: int,
) -> Tuple[bool, str]:
    """混合退出判断。

    退出条件（满足任一即退出）:
    1. pass_count >= PASS_COUNT_MIN AND llm_continue_loop == False
       → 结果数量达标且 LLM 认为充分
    2. loop_iter >= MAX_LOOPS
       → 达到硬上限，强制退出

    Returns:
        (continue_loop, reason)
    """
    if loop_iter >= MAX_LOOPS:
        return False, f"达到最大迭代轮次 {MAX_LOOPS}"

    if pass_count >= PASS_COUNT_MIN and not llm_continue_loop:
        return False, f"通过 {pass_count} 条（≥{PASS_COUNT_MIN}）且 LLM 判定充分"

    return True, f"需继续: passed={pass_count}/{PASS_COUNT_MIN}, llm_continue={llm_continue_loop}"


# =============================================================================
# 聚合统计
# =============================================================================


def aggregate_loop_summary(
    passed: List[CriticResult], total_count: int
) -> LoopSummary:
    """计算单轮迭代的聚合统计。

    TODO: dimensions_covered 当前为空，Search 适配（Step 5）后从
          ResearchResult 中获取维度信息。
    """
    if not passed:
        return LoopSummary(
            pass_count=0,
            total_count=total_count,
            avg_relevance=0.0,
            avg_utility=0.0,
            dimensions_covered=[],
        )

    avg_relevance = sum(r.relevance_score for r in passed) / len(passed)
    avg_utility = sum(r.utility_score for r in passed) / len(passed)

    return LoopSummary(
        pass_count=len(passed),
        total_count=total_count,
        avg_relevance=round(avg_relevance, 1),
        avg_utility=round(avg_utility, 1),
        dimensions_covered=[],  # Step 5 后补全
    )


# =============================================================================
# 主节点函数
# =============================================================================


async def critic_node(state: TravelState) -> Dict[str, Any]:
    """Critic 节点 — 三层过滤管线入口。

    读取 research_data.loop_state.query_results，经三层过滤后更新:
    - loop_state.passed_results（本轮通过）
    - loop_state.all_passed_results（累计通过）
    - loop_state.passed_queries（去重用）
    - loop_state.feedback（下一轮 QG 参考）
    - loop_state.continue_loop（是否继续循环）
    - loop_state.loop_summary（本轮统计）
    """
    start_time = time.time()
    logger.info("Critic: starting 3-layer evaluation pipeline")

    research_data = state.get("research_data")
    loop_state: ResearchLoopInternal = research_data.loop_state

    query_results_raw = loop_state.query_results
    total_count = len(query_results_raw)

    if total_count == 0:
        logger.info("Critic: no results to evaluate, skipping")
        return {
            "trace_history": [
                build_trace(
                    "critic",
                    "SKIPPED",
                    latency_ms=int((time.time() - start_time) * 1000),
                    detail={"reason": "query_results 为空"},
                )
            ]
        }

    # --- Layer 1: 黑名单过滤 ---
    blacklist = load_blacklist()
    # 将原始 dict 转为 ResearchResult 对象
    typed_results: Dict[str, ResearchResult] = {}
    for k, v in query_results_raw.items():
        if isinstance(v, ResearchResult):
            typed_results[k] = v
        elif isinstance(v, dict):
            typed_results[k] = ResearchResult(**v)
    passed_l1, _rejected_l1 = blacklist_filter(typed_results, blacklist)

    if not passed_l1:
        logger.info("Critic: all results filtered by blacklist")

    # --- Layer 2: LLM 评分（分批）---
    all_critic_results: List[CriticResult] = []
    llm_continue_loop = False
    llm_feedback = ""

    batch_items = list(passed_l1.items())
    for i in range(0, len(batch_items), CRITIC_BATCH_SIZE):
        batch = dict(batch_items[i : i + CRITIC_BATCH_SIZE])
        try:
            results, continue_loop, feedback = await llm_score_batch(batch)
            all_critic_results.extend(results)
            # 取最后一个批次的 continue_loop 决策（多批次时最后一组为准）
            llm_continue_loop = continue_loop
            llm_feedback = feedback
        except Exception as e:
            logger.error(f"Layer 2 评分失败 (batch {i}): {e}", exc_info=True)
            # 单批次失败不中断整体流程
            continue

    # --- Layer 3: 分数阈值过滤 ---
    passed_l3, _rejected_l3 = code_filter(all_critic_results)

    # --- 聚合统计 ---
    loop_summary = aggregate_loop_summary(passed_l3, total_count)

    # --- 循环退出决策 ---
    loop_iter = loop_state.loop_iteration
    continue_loop, exit_reason = should_continue_loop(
        len(passed_l3), llm_continue_loop, loop_iter
    )

    # --- 更新累计通过 ---
    previous_all_passed = list(loop_state.all_passed_results)
    all_passed_results = previous_all_passed + passed_l3
    passed_queries = list(loop_state.passed_queries)
    for r in passed_l3:
        if r.query not in passed_queries:
            passed_queries.append(r.query)

    # --- 构建新的 loop_state ---
    new_loop_state = ResearchLoopInternal(
        query_results=loop_state.query_results,
        passed_results=passed_l3,
        all_passed_results=all_passed_results,
        passed_queries=passed_queries,
        feedback=llm_feedback if continue_loop else None,
        continue_loop=continue_loop,
        loop_iteration=loop_iter + 1,
        loop_summary=loop_summary,
    )

    # 构建新的 research_data（更新 loop_state）
    new_research_data = research_data.model_copy(
        update={"loop_state": new_loop_state}
    )

    trace = build_trace(
        "critic",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "total": total_count,
            "l1_passed": len(passed_l1),
            "l2_scored": len(all_critic_results),
            "l3_passed": len(passed_l3),
            "continue_loop": continue_loop,
            "exit_reason": exit_reason,
            "avg_relevance": loop_summary.avg_relevance,
            "avg_utility": loop_summary.avg_utility,
        },
    )

    logger.info(
        f"Critic done: {total_count}→L1:{len(passed_l1)}→L3:{len(passed_l3)}, "
        f"continue_loop={continue_loop}, reason={exit_reason}"
    )

    return {
        "research_data": new_research_data,
        "trace_history": [trace],
    }

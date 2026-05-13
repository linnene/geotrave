"""
Module: src.agent.nodes.manager.node
Responsibility: Acts as the Brain/Router of the Agent.
Decides the next global stage (Loop, Recommender, Planner, or Reply)
based on execution signs, research manifests, and conversation context.
"""

import time
from typing import Any, Dict

from src.agent.state import TravelState, RouteMetadata, ManagerOutput
from src.agent.state.schema import ExecutionSigns, ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history
from .config import TEMPERATURE, MAX_TOKENS, HISTORY_LIMIT

from langchain_core.output_parsers import JsonOutputParser

logger = get_logger("ManagerNode")

parser = JsonOutputParser(pydantic_object=ManagerOutput)


async def manager_node(state: TravelState) -> Dict[str, Any]:
    """
    Manager Node — LLM 驱动的调度官。

    新设计哲学：调研一次即可推荐，不追求完美覆盖。
    LLM 提供意图分析，代码强制执行硬上限。
    """
    start_time = time.time()
    logger.info("Manager - Thinking about the next strategic step...")

    # 1. Prepare Context
    signs = state.get("execution_signs")
    research_manifest = state.get("research_data")
    messages = state.get("messages", [])

    # Diagnostic: log raw state to trace research_rounds / hashes through checkpoint
    _signs_type = type(signs).__name__ if signs is not None else "None"
    _signs_raw = signs.model_dump() if hasattr(signs, 'model_dump') else str(signs)
    _hashes_raw = research_manifest.research_hashes if research_manifest else None
    logger.info(
        "Manager DIAG: signs_type=%s signs=%s research_hashes=%s",
        _signs_type, _signs_raw, _hashes_raw,
    )

    is_core_complete = signs.is_core_complete if signs else False
    recommended_dimensions = getattr(signs, 'recommended_dimensions', []) or [] if signs else []
    research_rounds = signs.research_rounds if signs else 0
    research_hashes = research_manifest.research_hashes if research_manifest else {}
    hashes_count = sum(len(v) for v in research_hashes.values())
    research_history_full = research_manifest.research_history if research_manifest else []
    research_history = research_history_full[-10:]

    history = format_recent_history(messages, HISTORY_LIMIT)

    user_profile = state.get("user_profile")
    missing_fields = getattr(user_profile, 'all_missing_fields', []) or [] if user_profile else []

    # 2. LLM Orchestration
    prompt_str = prompt.manager.format(
        research_rounds=research_rounds,
        hashes_count=hashes_count,
        recommended_dimensions=", ".join(recommended_dimensions) if recommended_dimensions else "无",
        is_core_complete=is_core_complete,
        missing_fields=", ".join(missing_fields) if missing_fields else "无",
        research_history=research_history if research_history else "[]",
        history=history,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Manager", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        decision = await chain.ainvoke(prompt_str)
        if decision is None:
            raise ValueError("LLM returned empty or unparseable response")

        next_node = decision.get("next_stage")
        reason = decision.get("rationale", "无具体理由")
        focus_dimension = decision.get("focus_dimension")

        logger.info("Manager Decision: -> %s | Reason: %s", next_node.upper(), reason)
    except Exception as e:
        logger.error("Manager reasoning failed: %s", str(e), exc_info=True)
        next_node = "reply" if hashes_count == 0 else "recommender"
        reason = f"Fallback due to error: {str(e)}"
        focus_dimension = None

    # 3. Hard guards (code-enforced, overrides LLM)

    # Guard: is_core_complete=False blocks planner (needs full info), warns for recommender
    if not is_core_complete:
        if next_node == "planner":
            logger.warning(
                "Manager override: is_core_complete=False, blocking planner"
            )
            reason = f"[硬守卫] is_core_complete=False，阻止 planner（需完整画像）"
            next_node = "reply"
        elif next_node == "recommender":
            logger.warning(
                "Manager: is_core_complete=False but allowing recommender (partial data is fine)"
            )

    # Guard: recommender 前检查 focus_dimension 在 research_history 中的覆盖度
    # 若从未调研过该维度，且还有调研额度，先路由到 research_loop 补全数据
    if next_node == "recommender" and focus_dimension and research_rounds < 1:
        researched_dims = set()
        for entry in research_history_full:
            if entry.startswith("[") and "]" in entry:
                end = entry.index("]")
                if end > 1:
                    researched_dims.add(entry[1:end])
        if focus_dimension not in researched_dims:
            logger.warning(
                "Manager override: focus_dimension='%s' not in researched_dims=%s, "
                "routing to research_loop first to fill gap",
                focus_dimension, list(researched_dims),
            )
            next_node = "research_loop"
            reason = (
                f"[硬守卫] 维度 '{focus_dimension}' 从未被调研"
                f"（已调研: {', '.join(sorted(researched_dims)) or '无'}），"
                f"先执行 search 补全数据再推荐"
            )

    # Guard: research_rounds hard limit (max 1)
    if next_node == "research_loop":
        if research_rounds >= 1:
            if hashes_count > 0:
                next_node = "recommender"
                reason = f"[硬守卫] research_rounds={research_rounds} 已达上限，强制转为 recommender"
            else:
                next_node = "reply"
                reason = f"[硬守卫] research_rounds={research_rounds} 已达上限，且无调研数据，强制转为 reply"
            logger.warning("Manager hard guard: %s", reason)
        new_rounds = research_rounds + 1
    else:
        new_rounds = research_rounds

    # 4. Issue Routing Command
    route = RouteMetadata(
        next_node=next_node,
        reason=reason,
        focus_dimension=focus_dimension,
    )

    trace = build_trace(
        "manager",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "decision": next_node,
            "reason": reason,
            "hashes_count": hashes_count,
            "research_rounds": new_rounds,
            "research_history": research_history[-3:],
            "focus_dimension": focus_dimension,
        }
    )

    result: Dict[str, Any] = {
        "route_metadata": route,
        "execution_signs": ExecutionSigns.ensure(signs).model_copy(
            update={"research_rounds": new_rounds}
        ),
        "trace_history": [trace],
    }

    # 路由到 research_loop 时重置子图内部状态，并传递 focus_dimension 给 DimensionPlanner
    if next_node == "research_loop":
        if research_manifest:
            existing = result.get("research_data")
            if existing is None:
                result["research_data"] = research_manifest.model_copy(
                    update={"loop_state": ResearchLoopInternal()}
                )
        # 若 Manager 已指定目标维度，直接注入 state 供 DimensionPlanner 短接
        if focus_dimension:
            result["focus_dimension"] = focus_dimension

    return result

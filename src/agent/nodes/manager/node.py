"""
Module: src.agent.nodes.manager.node
Responsibility: Acts as the Brain/Router of the Agent.
Decides the next global stage (Loop, Recommender, Planner, or Reply)
based on execution signs, research manifests, and user selection context.
"""

import time
from typing import Any, Dict

from src.agent.state import TravelState, RouteMetadata, ManagerOutput
from src.agent.state.schema import ExecutionSigns, ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import manager_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, format_trace_history
from .config import TEMPERATURE, MAX_TOKENS, HISTORY_LIMIT, NODE_HISTORY_LIMIT

from langchain_core.output_parsers import JsonOutputParser

logger = get_logger("ManagerNode")

parser = JsonOutputParser(pydantic_object=ManagerOutput)


def _summarise_recommendation_data(state: TravelState) -> str:
    """Brief summary of recommendation_data for Manager context."""
    rec = state.get("recommendation_data")
    if not rec:
        return "暂无"
    parts = []
    for dim in ("destination", "accommodation", "dining"):
        dim_data = rec.get(dim)
        if dim_data:
            items = dim_data.get("items", [])
            names = [i.get("name", "") for i in items]
            parts.append(f"{dim}({len(items)}): {', '.join(names[:3])}")
    return " | ".join(parts) if parts else "暂无"


async def manager_node(state: TravelState) -> Dict[str, Any]:
    """
    Manager Node - The LLM-driven orchestrator.
    Decides the next global stage based on evidence from other nodes.
    """
    start_time = time.time()
    logger.info("Manager - Thinking about the next strategic step...")

    # 1. Prepare Context (Evidence-based)
    signs = state.get("execution_signs")
    research_manifest = state.get("research_data")
    messages = state.get("messages", [])

    is_safe = signs.is_safe if signs else True
    is_core_complete = signs.is_core_complete if signs else False
    is_recommendation_complete = signs.is_recommendation_complete if signs else False
    is_plan_complete = signs.is_plan_complete if signs else False
    is_selection_made = signs.is_selection_made if signs else False
    recommended_dimensions = getattr(signs, 'recommended_dimensions', []) or [] if signs else []
    research_hashes = research_manifest.research_hashes if research_manifest else {}
    hashes_count = sum(len(v) for v in research_hashes.values())
    research_history = research_manifest.research_history if research_manifest else []

    history = format_recent_history(messages, HISTORY_LIMIT)
    user_request = state.get("user_request", "未知诉求")
    rec_summary = _summarise_recommendation_data(state)

    trace_logs = state.get("trace_history", [])
    trace_history_str = format_trace_history(trace_logs, 5)

    research_matches_current = (
        research_history[-1] == user_request
        if research_history
        else False
    )

    # 2. LLM Orchestration
    prompt_str = manager_prompt_template.format(
        is_safe=is_safe,
        is_core_complete=is_core_complete,
        is_recommendation_complete=is_recommendation_complete,
        is_plan_complete=is_plan_complete,
        is_selection_made=is_selection_made,
        recommended_dimensions=", ".join(recommended_dimensions) if recommended_dimensions else "无",
        recommendation_summary=rec_summary,
        hashes_count=hashes_count,
        research_matches_current=research_matches_current,
        research_history=research_history if research_history else "[]",
        history=history,
        user_request=user_request,
        trace_history=trace_history_str,
        format_instructions=parser.get_format_instructions()
    )

    llm = LLMFactory.get_model("Manager", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        decision = await chain.ainvoke(prompt_str)

        next_node = decision.get("next_stage")
        reason = decision.get("rationale", "无具体理由")
        user_selections = decision.get("user_selections")

        logger.info(f"Manager Decision: -> {next_node.upper()} | Reason: {reason}")
    except Exception as e:
        logger.error(f"Manager reasoning failed: {str(e)}", exc_info=True)
        next_node = "reply" if not is_core_complete else "research_loop"
        reason = f"Fallback due to error: {str(e)}"
        user_selections = None

    # 硬守卫: is_core_complete=False 时必须导向 reply
    if not is_core_complete and next_node != "reply":
        logger.warning(
            f"Manager override: is_core_complete=False, forcing reply (was: {next_node})"
        )
        reason = f"[硬守卫覆写] is_core_complete 为 False，强制导向 reply。原决策: {next_node}，原理由: {reason}"
        next_node = "reply"

    # 3. Issue Routing Command
    route = RouteMetadata(
        next_node=next_node,
        reason=reason,
        is_error=False
    )

    trace = build_trace(
        "manager",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "decision": next_node,
            "reason": reason,
            "hashes_count": hashes_count,
            "research_history": research_history[-3:],
            "has_user_selections": user_selections is not None,
        }
    )

    result: Dict[str, Any] = {
        "route_metadata": route,
        "trace_history": [trace],
    }

    # 写入用户选择到 state
    if user_selections is not None:
        result["user_selections"] = user_selections
        result["execution_signs"] = (signs or ExecutionSigns()).model_copy(
            update={"is_selection_made": True}
        )

    # 路由到 research_loop 时重置内部状态
    if next_node == "research_loop" and research_manifest:
        existing = result.get("research_data")
        if existing is None:
            result["research_data"] = research_manifest.model_copy(
                update={"loop_state": ResearchLoopInternal()}
            )

    return result

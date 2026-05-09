"""
Module: src.agent.nodes.manager.node
Responsibility: Acts as the Brain/Router of the Agent.
Decides the next global stage (Loop, Recommender, Planner, or Reply)
based on execution signs, research manifests, and conversation context.
"""

import time
from typing import Any, Dict

from src.agent.state import TravelState, RouteMetadata, ManagerOutput
from src.agent.state.schema import ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, format_trace_history
from .config import TEMPERATURE, MAX_TOKENS, HISTORY_LIMIT

from langchain_core.output_parsers import JsonOutputParser

logger = get_logger("ManagerNode")

parser = JsonOutputParser(pydantic_object=ManagerOutput)


def _summarise_recommendation_data(state: TravelState) -> str:
    """Brief summary of recommendation_data for Manager context."""
    rec = state.get("recommendation_data")
    if not rec:
        return "暂无"
    parts = []
    for dim, dim_data in rec.items():
        names = [i.name for i in dim_data.items]
        parts.append(f"{dim}({len(dim_data.items)}): {', '.join(names[:3])}")
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
    recommended_dimensions = getattr(signs, 'recommended_dimensions', []) or [] if signs else []
    research_hashes = research_manifest.research_hashes if research_manifest else {}
    hashes_count = sum(len(v) for v in research_hashes.values())
    research_history_full = research_manifest.research_history if research_manifest else []
    research_history = research_history_full[-10:]  # 只保留最近 10 条，防止污染 Manager 判断

    history = format_recent_history(messages, HISTORY_LIMIT)
    rec_summary = _summarise_recommendation_data(state)

    trace_logs = state.get("trace_history", [])
    trace_history_str = format_trace_history(trace_logs, 5)

    user_profile = state.get("user_profile")
    missing_fields = getattr(user_profile, 'all_missing_fields', []) or [] if user_profile else []

    # 2. LLM Orchestration
    prompt_str = prompt.manager.format(
        is_safe=is_safe,
        is_core_complete=is_core_complete,
        is_recommendation_complete=is_recommendation_complete,
        is_plan_complete=is_plan_complete,
        recommended_dimensions=", ".join(recommended_dimensions) if recommended_dimensions else "无",
        recommendation_summary=rec_summary,
        hashes_count=hashes_count,
        research_history=research_history if research_history else "[]",
        history=history,
        trace_history=trace_history_str,
        missing_fields=", ".join(missing_fields) if missing_fields else "无",
        format_instructions=parser.get_format_instructions()
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
        next_node = "reply" if not is_core_complete else "research_loop"
        reason = f"Fallback due to error: {str(e)}"
        focus_dimension = None

    # 软守卫: is_core_complete=False 时阻止推荐/规划（需完整上下文），但允许研究先行
    if not is_core_complete and next_node in ("recommender", "planner"):
        logger.warning(
            f"Manager override: is_core_complete=False, blocking {next_node} (requires full profile)"
        )
        reason = f"[软守卫覆写] is_core_complete 为 False，阻止 {next_node}（需完整画像），回退到 reply"
        next_node = "reply"

    # 3. Issue Routing Command
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
            "research_history": research_history[-3:],
            "focus_dimension": focus_dimension,
        }
    )

    result: Dict[str, Any] = {
        "route_metadata": route,
        "trace_history": [trace],
    }

    # 路由到 research_loop 时重置内部状态
    if next_node == "research_loop" and research_manifest:
        existing = result.get("research_data")
        if existing is None:
            result["research_data"] = research_manifest.model_copy(
                update={"loop_state": ResearchLoopInternal()}
            )

    return result

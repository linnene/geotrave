"""
Module: src.agent.nodes.planner.node
Responsibility: Generates day-by-day itineraries based on real research data,
               recommendations, user selections, and user profile.
               Routes to END — API returns itinerary to frontend.
"""

import json
import time
from typing import Any, Dict

from src.agent.state import TravelState
from src.agent.state.schema import ExecutionSigns, PlannerOutput, UserSelections
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import planner_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, fetch_research_content, get_beijing_time_now

from langchain_core.output_parsers import JsonOutputParser

from .config import HISTORY_LIMIT, MAX_TOKENS, TEMPERATURE

logger = get_logger("PlannerNode")

parser = JsonOutputParser(pydantic_object=PlannerOutput)


def _summarise_recommendations(state: TravelState) -> str:
    """Build a structured summary of recommendation data for the prompt."""
    rec_data = state.get("recommendation_data")
    if not rec_data:
        return "暂无推荐数据"

    lines = []
    for key, label in [("destinations", "目的地"), ("accommodations", "住宿"), ("dining", "餐饮")]:
        items = rec_data.get(key, [])
        if items:
            lines.append(f"**{label}**:")
            for item in items[:5]:
                lines.append(
                    f"  - {item.get('name', 'N/A')} (评分 {item.get('score', '?')}/100): "
                    f"{item.get('rationale', '')[:120]}"
                )
    if not lines:
        return "推荐数据为空"
    return "\n".join(lines)


def _summarise_user_selections(state: TravelState) -> str:
    """Build a summary of user selections that constrains Planner output."""
    sel_data = state.get("user_selections")
    if not sel_data:
        return "用户尚未做出选择（由 Planner 从推荐中自由选取最优项）"

    se = UserSelections(**sel_data) if isinstance(sel_data, dict) else sel_data

    # User delegated authority
    all_agent = all(
        (getattr(se, f, None) == "agent_choice" or getattr(se, f, None) is None)
        for f in ["chosen_destination", "chosen_accommodation", "chosen_dining"]
    )
    if all_agent and not se.needs_reselect:
        return "用户表示'随便/都行'，由 Planner 从推荐中自由选取最优项"

    lines = ["**用户已做出以下选择，Planner 必须严格遵守**:"]
    if se.chosen_destination and se.chosen_destination != "agent_choice":
        lines.append(f"- 目的地: {se.chosen_destination}")
    elif se.chosen_destination == "agent_choice":
        lines.append("- 目的地: 用户放弃选择权，从推荐中选最优")
    if se.chosen_accommodation and se.chosen_accommodation != "agent_choice":
        lines.append(f"- 住宿: {se.chosen_accommodation}")
    if se.chosen_dining and se.chosen_dining != "agent_choice":
        lines.append(f"- 餐饮: {se.chosen_dining}")
    return "\n".join(lines)


async def planner_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()
    logger.info("Planner — generating day-by-day itinerary...")

    messages = state.get("messages", [])
    user_profile = state.get("user_profile")
    user_request = state.get("user_request", "")
    research_manifest = state.get("research_data")

    history = format_recent_history(messages, HISTORY_LIMIT)
    research_summary = await fetch_research_content(research_manifest)
    rec_summary = _summarise_recommendations(state)
    sel_summary = _summarise_user_selections(state)
    profile_json = user_profile.model_dump_json(indent=2, ensure_ascii=False) if user_profile else "{}"

    prompt_str = planner_prompt_template.format(
        current_time=get_beijing_time_now(),
        history=history,
        user_request=user_request,
        user_profile=profile_json,
        research_summary=research_summary,
        recommendations=rec_summary,
        user_selections=sel_summary,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Planner", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        raw: dict = await chain.ainvoke(prompt_str)
        plan = PlannerOutput(**raw)
        logger.info(f"Planner done — {len(plan.days)} days planned")
    except Exception as exc:
        logger.error(f"Planner LLM call failed: {exc}", exc_info=True)
        plan = PlannerOutput(
            days=[],
            notes=[f"行程生成失败: {str(exc)[:200]}"],
        )

    trace = build_trace(
        "planner",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "days_count": len(plan.days),
            "activities_total": sum(len(d.activities) for d in plan.days),
        },
    )

    return {
        "plan_data": plan.model_dump(),
        "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(
            update={"is_plan_complete": True}
        ),
        "trace_history": [trace],
    }

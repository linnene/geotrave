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
from src.agent.state.schema import ExecutionSigns, PlannerOutput
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
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

    dim_labels = {"destination": "目的地", "accommodation": "住宿", "dining": "餐饮"}
    lines = []
    for dim, label in dim_labels.items():
        dim_out = rec_data.get(dim)
        if dim_out and dim_out.items:
            lines.append(f"**{label}**:")
            for item in dim_out.items[:5]:
                rating = item.rating
                stars = "★" * int(rating) + ("☆" if rating - int(rating) >= 0.5 else "")
                lines.append(
                    f"  - {item.name} ({stars} {rating}/5): "
                    f"{item.reason[:120]}"
                )
    if not lines:
        return "推荐数据为空"
    return "\n".join(lines)


async def planner_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()
    logger.info("Planner — generating day-by-day itinerary...")

    messages = state.get("messages", [])
    user_profile = state.get("user_profile")
    research_manifest = state.get("research_data")

    history = format_recent_history(messages, HISTORY_LIMIT)
    research_summary = await fetch_research_content(research_manifest)
    rec_summary = _summarise_recommendations(state)
    profile_json = user_profile.model_dump_json(indent=2, ensure_ascii=False) if user_profile else "{}"

    prompt_str = prompt.planner.format(
        current_time=get_beijing_time_now(),
        history=history,
        user_profile=profile_json,
        research_summary=research_summary,
        recommendations=rec_summary,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Planner", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        raw = await chain.ainvoke(prompt_str)
        if raw is None:
            raise ValueError("LLM returned empty or unparseable response")
        plan = PlannerOutput(**raw)
        logger.info(f"Planner done — {len(plan.days)} days planned")
    except Exception as exc:
        logger.error(f"Planner LLM call failed: {exc}", exc_info=True)
        plan = PlannerOutput(
            days=[],
            notes=[f"行程生成失败: {str(exc)[:200]}"],
        )
        plan_failed = True
    else:
        plan_failed = False

    trace = build_trace(
        "planner",
        "FAIL" if plan_failed else "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "days_count": len(plan.days),
            "activities_total": sum(len(d.activities) for d in plan.days),
        },
    )

    return {
        "plan_data": plan,
        "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(
            update={"is_plan_complete": not plan_failed}
        ),
        "trace_history": [trace],
    }

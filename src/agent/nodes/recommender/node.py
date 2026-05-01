"""
Module: src.agent.nodes.recommender.node
Responsibility: Generates destination, accommodation, and dining recommendations
               based on real Research Loop results (from Retrieval DB) and UserProfile.
               Routes to END — API returns recommendations to frontend for user selection.
"""

import time
from typing import Any, Dict

from src.agent.state import TravelState
from src.agent.state.schema import ExecutionSigns, RecommenderOutput
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import recommender_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, fetch_research_content, get_beijing_time_now

from langchain_core.output_parsers import JsonOutputParser

from .config import HISTORY_LIMIT, MAX_TOKENS, TEMPERATURE

logger = get_logger("RecommenderNode")

parser = JsonOutputParser(pydantic_object=RecommenderOutput)


async def recommender_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()
    logger.info("Recommender — generating destination/accommodation/dining recommendations...")

    messages = state.get("messages", [])
    user_profile = state.get("user_profile")
    user_request = state.get("user_request", "")
    research_manifest = state.get("research_data")

    history = format_recent_history(messages, HISTORY_LIMIT)
    research_summary = await fetch_research_content(research_manifest)
    profile_json = user_profile.model_dump_json(indent=2, ensure_ascii=False) if user_profile else "{}"

    prompt_str = recommender_prompt_template.format(
        current_time=get_beijing_time_now(),
        history=history,
        user_request=user_request,
        user_profile=profile_json,
        research_summary=research_summary,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Recommender", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        raw: dict = await chain.ainvoke(prompt_str)
        rec = RecommenderOutput(**raw)
        logger.info(
            f"Recommender done — {len(rec.destinations)} destinations, "
            f"{len(rec.accommodations)} accommodations, {len(rec.dining)} dining"
        )
    except Exception as exc:
        logger.error(f"Recommender LLM call failed: {exc}", exc_info=True)
        rec = RecommenderOutput(
            destinations=[],
            accommodations=[],
            dining=[],
            strategy=f"推荐生成失败: {str(exc)[:200]}",
        )

    trace = build_trace(
        "recommender",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "destinations_count": len(rec.destinations),
            "accommodations_count": len(rec.accommodations),
            "dining_count": len(rec.dining),
        },
    )

    return {
        "recommendation_data": rec.model_dump(),
        "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(
            update={"is_recommendation_complete": True}
        ),
        "trace_history": [trace],
    }

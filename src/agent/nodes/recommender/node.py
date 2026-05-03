"""
Module: src.agent.nodes.recommender.node
Responsibility: Generates single-dimension destination/accommodation/dining recommendations
               based on Research Loop results and UserProfile.
               Each call focuses on ONE dimension only; Manager may call multiple times.
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

# 推荐的默认优先级顺序
_DIMENSION_PRIORITY = ("destination", "accommodation", "dining")


def _next_dimension(recommended_dimensions: list) -> str:
    """返回下一个应该推荐的维度。按 destination → accommodation → dining 顺序。"""
    for dim in _DIMENSION_PRIORITY:
        if dim not in recommended_dimensions:
            return dim
    return ""


async def recommender_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()

    signs = state.get("execution_signs")
    recommended_dimensions = list(getattr(signs, 'recommended_dimensions', []) or []) if signs else []
    focus_dim = _next_dimension(recommended_dimensions)

    if not focus_dim:
        logger.warning("Recommender called but all dimensions already covered")
        return {
            "execution_signs": (signs or ExecutionSigns()).model_copy(
                update={"is_recommendation_complete": True}
            ),
        }

    logger.info(f"Recommender — generating {focus_dim} recommendations...")

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
        focus_dimension=focus_dim,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Recommender", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        raw: dict = await chain.ainvoke(prompt_str)
        rec = RecommenderOutput(**raw)
        logger.info(
            f"Recommender done — dimension={rec.dimension}, {len(rec.items)} items"
        )
    except Exception as exc:
        logger.error(f"Recommender LLM call failed: {exc}", exc_info=True)
        rec = RecommenderOutput(
            dimension=focus_dim,
            items=[],
            strategy=f"推荐生成失败: {str(exc)[:200]}",
            tip="请稍后重试或换一个维度",
        )

    # 累积存储：按维度写入 recommendation_data
    existing_recs = state.get("recommendation_data") or {}
    existing_recs[rec.dimension] = rec.model_dump()

    # 追加已覆盖维度
    new_dimensions = list(recommended_dimensions)
    if rec.dimension not in new_dimensions:
        new_dimensions.append(rec.dimension)

    trace = build_trace(
        "recommender",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "dimension": rec.dimension,
            "items_count": len(rec.items),
            "recommended_dimensions": new_dimensions,
        },
    )

    return {
        "recommendation_data": existing_recs,
        "execution_signs": (signs or ExecutionSigns()).model_copy(
            update={"recommended_dimensions": new_dimensions}
        ),
        "trace_history": [trace],
    }

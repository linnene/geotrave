"""
Module: src.agent.nodes.recommender.node
Responsibility: Generates single-dimension recommendations based on Research Loop results
               and UserProfile. Dimension is driven by Manager's focus_dimension hint.
               Each call focuses on ONE dimension only; Manager may call multiple times.
"""

import time
from typing import Any, Dict

from src.agent.state import TravelState
from src.agent.state.schema import ExecutionSigns, RecommenderOutput
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, fetch_research_content, get_beijing_time_now

from langchain_core.output_parsers import JsonOutputParser

from .config import HISTORY_LIMIT, MAX_TOKENS, TEMPERATURE

logger = get_logger("RecommenderNode")

parser = JsonOutputParser(pydantic_object=RecommenderOutput)


def _resolve_dimension(focus_hint: str | None) -> str | None:
    """返回本轮推荐维度。直接使用 Manager 传入的 focus_dimension hint。"""
    if focus_hint:
        return focus_hint
    return None


async def recommender_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()

    signs = state.get("execution_signs")
    recommended_dimensions = list(getattr(signs, 'recommended_dimensions', []) or []) if signs else []

    # 读取 Manager 传入的维度提示（用户明确请求某维度时）
    route_meta = state.get("route_metadata")
    focus_hint = getattr(route_meta, 'focus_dimension', None) if route_meta else None

    focus_dim = _resolve_dimension(focus_hint)

    if not focus_dim:
        logger.warning("Recommender called without focus_dimension hint from Manager")
        return {
            "execution_signs": (signs or ExecutionSigns()).model_copy(
                update={"is_recommendation_complete": True}
            ),
        }

    logger.info(f"Recommender — generating {focus_dim} recommendations...")

    messages = state.get("messages", [])
    user_profile = state.get("user_profile")
    research_manifest = state.get("research_data")

    history = format_recent_history(messages, HISTORY_LIMIT)
    research_summary = await fetch_research_content(research_manifest)
    profile_json = user_profile.model_dump_json(indent=2, ensure_ascii=False) if user_profile else "{}"

    prompt_str = prompt.recommender.format(
        current_time=get_beijing_time_now(),
        history=history,
        user_profile=profile_json,
        research_summary=research_summary,
        focus_dimension=focus_dim,
        format_instructions=parser.get_format_instructions(),
    )

    llm = LLMFactory.get_model("Recommender", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        chain = llm | parser
        raw = await chain.ainvoke(prompt_str)
        if raw is None:
            raise ValueError("LLM returned empty or unparseable response")
        rec = RecommenderOutput(**raw)
        logger.info(
            f"Recommender done — dimension={rec.dimension}, {len(rec.items)} items"
        )
        for idx, item in enumerate(rec.items, 1):
            logger.info(
                f"  [{idx}] {item.name} | rating={item.rating} | {item.features} | reason={item.reason}"
            )
    except Exception as exc:
        logger.error(f"Recommender LLM call failed: {exc}", exc_info=True)
        rec = RecommenderOutput(
            dimension=focus_dim,
            items=[],
            strategy=f"推荐生成失败: {str(exc)[:200]}",
            tip="请稍后重试或换一个维度",
        )
        rec_failed = True
    else:
        rec_failed = False

    # 累积存储：按维度写入 recommendation_data (直接存模型，非 dict)
    existing_recs = state.get("recommendation_data") or {}
    existing_recs[rec.dimension] = rec

    # 追加已覆盖维度（仅在成功时标记维度已覆盖）
    new_dimensions = list(recommended_dimensions)
    if not rec_failed and rec.dimension not in new_dimensions:
        new_dimensions.append(rec.dimension)

    trace = build_trace(
        "recommender",
        "FAIL" if rec_failed else "SUCCESS",
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

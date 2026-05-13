import time
import json
from typing import Any, Dict

from src.agent.state import TravelState, DimensionPlannerOutput
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, extract_content_str, format_recent_history
from .config import TEMPERATURE, HISTORY_LIMIT, MAX_TOKENS

logger = get_logger("DimensionPlannerNode")


def _get_format_instructions() -> str:
    return json.dumps(DimensionPlannerOutput.model_json_schema(), indent=2, ensure_ascii=False)


async def dimension_planner_node(state: TravelState) -> Dict[str, Any]:
    """DimensionPlanner Node — 接替 Manager 和 QG 的维度解耦职责。

    从对话历史和用户画像中独立分析需要检索的维度，
    输出 planned_dimensions 和 dimension_hints 供 Send 扇出使用。

    当 Manager 已在 state 中预设 focus_dimension 时（覆盖度不足主动补全场景），
    直接使用该维度，跳过 LLM 分析。
    """
    start_time = time.time()
    logger.info("Planning research dimensions at [DimensionPlanner]...")

    # Manager 预设维度：覆盖度不足时主动补全，跳过 LLM 分析
    pre_set_dim = state.get("focus_dimension")
    if pre_set_dim:
        logger.info(
            "DimensionPlanner → using Manager pre-set dimension: %s", pre_set_dim
        )
        return {
            "planned_dimensions": [pre_set_dim],
            "dimension_hints": {pre_set_dim: f"{pre_set_dim}相关信息"},
            "trace_history": [
                build_trace(
                    "dimension_planner",
                    "SUCCESS",
                    latency_ms=int((time.time() - start_time) * 1000),
                    detail={
                        "dimensions": [pre_set_dim],
                        "rationale": "Manager pre-set dimension (coverage gap fill)",
                    },
                )
            ],
        }

    messages = state.get("messages", [])
    history = format_recent_history(messages, HISTORY_LIMIT)

    user_profile = state.get("user_profile")
    profile_json = user_profile.model_dump_json(indent=2) if user_profile else "{}"

    # 获取已有调研历史，避免重复规划
    research_data = state.get("research_data")
    existing_history = research_data.research_history if research_data else []
    existing_str = "\n".join(f"- {h}" for h in existing_history[-5:]) if existing_history else "无"

    # 提取目的地，直接注入提示词防止维度漂移
    dest_list = (user_profile.destination or []) if user_profile else []
    destination_context = dest_list[0] if dest_list else "未指定"

    format_instructions = _get_format_instructions()

    # 读取 Manager 的缺口分析，使 DimensionPlanner 了解为何被重新调度
    route_meta = state.get("route_metadata")
    manager_hint = route_meta.reason if route_meta else ""

    prompt_str = prompt.dimension_planner.format(
        history=history,
        user_profile=profile_json,
        existing_research=existing_str,
        destination=destination_context,
        format_instructions=format_instructions,
        manager_hint=manager_hint,
    )

    llm = LLMFactory.get_model("DimensionPlanner", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    bound_llm = llm.bind(response_format={"type": "json_object"})

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        content = extract_content_str(raw_result)
        parsed = json.loads(content)
        result = DimensionPlannerOutput(**parsed)

        # 按 priority 降序排列，硬上限最多 3 个维度
        sorted_dims = sorted(result.dimensions, key=lambda d: d.priority, reverse=True)
        sorted_dims = sorted_dims[:3]
        dim_names = [d.name for d in sorted_dims]
        dim_hints = {d.name: d.focus for d in sorted_dims}

        logger.info(
            "DimensionPlanner → %d dimensions: %s | Rationale: %s",
            len(dim_names), ", ".join(dim_names), result.rationale
        )

        trace = build_trace(
            "dimension_planner",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={
                "dimensions": dim_names,
                "hints": dim_hints,
                "rationale": result.rationale,
            }
        )

        return {
            "planned_dimensions": dim_names,
            "dimension_hints": dim_hints,
            "trace_history": [trace],
        }

    except Exception as e:
        logger.error("DimensionPlanner execution failed: %s", str(e), exc_info=True)
        # Fallback: 通用维度作为兜底
        fallback = ["attraction", "general"]
        trace = build_trace(
            "dimension_planner",
            "FAIL",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"error": str(e), "fallback": fallback}
        )
        return {
            "planned_dimensions": fallback,
            "dimension_hints": {"attraction": "主要景点", "general": "综合信息"},
            "trace_history": [trace],
        }

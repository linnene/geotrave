import time
import json
from typing import Dict, Any

from src.agent.state import TravelState, QueryGeneratorOutput, ResearchManifest
from src.agent.state.schema import ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, extract_content_str, format_recent_history, get_beijing_time_now
from .config import TEMPERATURE, HISTORY_LIMIT, MAX_TOKENS

logger = get_logger("QueryGeneratorNode")

def _get_format_instructions() -> str:
    """Extracts and formats the JSON schema from QueryGeneratorOutput for LLM guidance."""
    return json.dumps(QueryGeneratorOutput.model_json_schema(), indent=2, ensure_ascii=False)

def _get_tools_documentation() -> str:
    """
    动态从 Search 节点的工具注册中心获取可用工具列表，
    以保证提示词中的工具信息与实际可执行工具一致。
    """
    from ..search.tools import TOOL_METADATA
    return json.dumps(TOOL_METADATA, indent=2, ensure_ascii=False)

PLACEHOLDER_VALUES = {"未指定", "未設定", "unspecified", "none", "null", ""}
BLOCKED_CITIES = {"东京", "東京", "Tokyo", "大阪", "Osaka", "大阪市", "京都", "Kyoto", "名古屋", "Nagoya", "福岡", "Fukuoka"}


def _first_destination(user_profile) -> str:
    """Extract the primary destination name from UserProfile."""
    if not user_profile or not user_profile.destination:
        return ""
    return user_profile.destination[0] or ""


def _is_foreign_city(value: str, destination: str) -> bool:
    """Check if a value is a known foreign city that doesn't match the user's destination."""
    if not value or not destination:
        return False
    v = value.strip()
    if v.lower() in BLOCKED_CITIES or v in BLOCKED_CITIES:
        return v != destination and destination not in v
    return False


def _validated_param(params: dict, key: str, destination: str, task_name: str) -> bool:
    """If params[key] is empty or a blocked city, replace it with destination. Returns True if fixed."""
    value = (params.get(key) or "").strip()
    if not value or _is_foreign_city(value, destination) or value.lower() in PLACEHOLDER_VALUES or value in PLACEHOLDER_VALUES:
        logger.warning("QG generated invalid %s %s=%r, replacing with destination=%r", task_name, key, value, destination)
        params[key] = destination
        return True
    return False


def _enforce_destination(tasks, destination: str):
    """Replace empty/placeholder/foreign-city centers with the actual destination.

    The LLM occasionally injects placeholder values like "未指定", or picks a completely
    unrelated city (e.g. Tokyo instead of Sapporo). This is a code-level safety net that
    covers all location-bearing tool parameters.
    """
    new_tasks = []
    for task in tasks:
        fixed = False
        params = {**task.parameters}
        if task.tool_name == "spatial_search":
            fixed = _validated_param(params, "center", destination, "spatial_search")
        elif task.tool_name == "route_search":
            for key in ("origin", "destination"):
                if _validated_param(params, key, destination, "route_search"):
                    fixed = True
        elif task.tool_name == "weather_search":
            fixed = _validated_param(params, "location", destination, "weather_search")
        elif task.tool_name == "document_search":
            fixed = _validated_param(params, "place_filter", destination, "document_search")
        if fixed:
            new_tasks.append(task.model_copy(update={"parameters": params}))
        else:
            new_tasks.append(task)
    return new_tasks


async def query_generator_node(state: TravelState) -> Dict[str, Any]:
    """Query Generator Node — 调研方案规划。

    从 UserProfile 和对话历史出发，生成 SearchTask 列表。
    当 focus_dimension 被设置时（并行模式），仅在指定维度内生成任务。
    支持多轮 Research Loop：接收 Critic 反馈和已通过查询，避免重复生成。
    """
    start_time = time.time()

    # 0. 检查并行模式 — focus_dimension 由 Send 扇出时注入
    focus_dimension = state.get("focus_dimension")
    hints = state.get("dimension_hints", {})
    focus_hint = hints.get(focus_dimension, "") if focus_dimension else ""

    user_profile = state.get("user_profile")

    # Code-level destination injection — 防止 LLM 在 focus_hint 中丢失目的地
    user_dest = _first_destination(user_profile)
    if user_dest and focus_hint:
        focus_hint = f"[目的地={user_dest}] {focus_hint}"
    elif user_dest:
        focus_hint = f"目的地: {user_dest}"

    dim_tag = f"[{focus_dimension}] " if focus_dimension else ""
    dim_ctx = {"dimension": focus_dimension} if focus_dimension else {}
    if focus_dimension:
        logger.info("%sGenerating focused research plan at [QueryGenerator]...", dim_tag)
    else:
        logger.info("Generating research plan at [QueryGenerator]...")

    # 1. Prepare Context — QG 自行从对话历史中分析用户意图
    messages = state.get("messages", [])
    history = format_recent_history(messages, HISTORY_LIMIT)

    # 2. Extract loop_state data (Critic feedback + passed queries)
    research_data = state.get("research_data")
    loop_state = research_data.loop_state if research_data else None
    feedback = loop_state.feedback if loop_state else None
    passed_queries = loop_state.passed_queries if loop_state else []

    feedback_str = feedback if feedback else "无（首轮调研）"
    passed_queries_str = "\n".join(f"- {q}" for q in passed_queries[-10:]) if passed_queries else "无（首轮调研）"

    # 3. Dynamic Injection
    tools_doc = _get_tools_documentation()
    format_instructions = _get_format_instructions()

    prompt_str = prompt.query_generator.format(
        current_time=get_beijing_time_now(),
        user_profile=user_profile.model_dump_json(indent=2) if user_profile else "{}",
        tools_doc=tools_doc,
        format_instructions=format_instructions,
        history=history,
        missing_fields=", ".join(user_profile.all_missing_fields) if user_profile and user_profile.all_missing_fields else "无核心缺失",
        feedback=feedback_str,
        passed_queries=passed_queries_str,
        focus_dimension=focus_dimension or "无（全维度搜索模式）",
        focus_hint=focus_hint or "无",
    )

    # 4. LLM Orchestration
    llm = LLMFactory.get_model("QueryGenerator", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    bound_llm = llm.bind(response_format={"type": "json_object"})

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        content = extract_content_str(raw_result)
        parsed_json = json.loads(content)
        result = QueryGeneratorOutput(**parsed_json)

        # 5.5. Code-level destination enforcement — 防止 LLM 注入未指定/空 center
        destination = _first_destination(user_profile)
        if destination:
            validated_tasks = _enforce_destination(result.tasks, destination)
            if validated_tasks is not result.tasks:
                result = result.model_copy(update={"tasks": validated_tasks})

        # 6. Update ResearchManifest — 将 tasks 写入 loop_state.active_queries
        # 将 research_strategy 追加到 research_history，供 Manager 判断调研新鲜度
        old_history = research_data.research_history if research_data else []
        current_strategy = result.research_strategy

        new_history = old_history[:]
        if not new_history or new_history[-1] != current_strategy:
            new_history.append(current_strategy)
        new_history = new_history[-10:]  # cap to last 10 entries

        if research_data:
            new_research_data = research_data.model_copy(
                update={
                    "research_history": new_history,
                    "loop_state": research_data.loop_state.model_copy(
                        update={"active_queries": result.tasks}
                    ),
                }
            )
        else:
            new_research_data = ResearchManifest(
                research_history=new_history,
                loop_state=ResearchLoopInternal(active_queries=result.tasks),
            )

        trace = build_trace(
            "query_generator",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={
                "task_count": len(result.tasks),
                "strategy": result.research_strategy,
                **dim_ctx,
            }
        )

        return {
            "research_data": new_research_data,
            "trace_history": [trace],
        }

    except Exception as e:
        logger.error("%sQueryGenerator execution failed: %s", dim_tag, str(e), exc_info=True)
        trace = build_trace(
            "query_generator",
            "FAIL",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"error": str(e), **dim_ctx}
        )
        return {"trace_history": [trace]}

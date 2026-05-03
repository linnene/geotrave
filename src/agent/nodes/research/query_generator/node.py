import time
import json
from typing import Dict, Any

from src.agent.state import TravelState, QueryGeneratorOutput, ResearchManifest
from src.agent.state.schema import ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import query_generator_prompt_template
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

async def query_generator_node(state: TravelState) -> Dict[str, Any]:
    """Query Generator Node — 多维调研方案规划。

    从 UserProfile 和对话历史出发，生成 SearchTask 列表。
    支持多轮 Research Loop：接收 Critic 反馈和已通过查询，避免重复生成。
    """
    start_time = time.time()
    logger.info("Generating research plan at [QueryGenerator]...")

    # 1. Prepare Context
    messages = state.get("messages", [])
    history = format_recent_history(messages, HISTORY_LIMIT)

    user_profile = state.get("user_profile")
    user_request = state.get("user_request", "无明确诉求")

    # 2. Extract loop_state data (Critic feedback + passed queries)
    research_data = state.get("research_data")
    loop_state = research_data.loop_state if research_data else None
    feedback = loop_state.feedback if loop_state else None
    passed_queries = loop_state.passed_queries if loop_state else []

    feedback_str = feedback if feedback else "无（首轮调研）"
    passed_queries_str = "\n".join(f"- {q}" for q in passed_queries) if passed_queries else "无（首轮调研）"

    # 3. Dynamic Injection
    tools_doc = _get_tools_documentation()
    format_instructions = _get_format_instructions()

    prompt_str = query_generator_prompt_template.format(
        current_time=get_beijing_time_now(),
        user_profile=user_profile.model_dump_json(indent=2) if user_profile else "{}",
        user_request=user_request,
        tools_doc=tools_doc,
        format_instructions=format_instructions,
        history=history,
        missing_fields=", ".join(state.get("missing_fields", [])) if state.get("missing_fields") else "无核心缺失",
        feedback=feedback_str,
        passed_queries=passed_queries_str,
    )

    # 4. LLM Orchestration
    llm = LLMFactory.get_model("QueryGenerator", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    bound_llm = llm.bind(response_format={"type": "json_object"})

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        content = extract_content_str(raw_result)
        parsed_json = json.loads(content)
        result = QueryGeneratorOutput(**parsed_json)

        # 5. Update ResearchManifest — 将 tasks 写入 loop_state.active_queries
        old_history = research_data.research_history if research_data else []
        current_request = state.get("user_request", "")

        if research_data:
            new_research_data = research_data.model_copy(
                update={
                    "research_history": old_history + [current_request],
                    "loop_state": research_data.loop_state.model_copy(
                        update={"active_queries": result.tasks}
                    ),
                }
            )
        else:
            new_research_data = ResearchManifest(
                research_history=[current_request],
                loop_state=ResearchLoopInternal(active_queries=result.tasks),
            )

        trace = build_trace(
            "query_generator",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={
                "task_count": len(result.tasks),
                "strategy": result.research_strategy,
            }
        )

        return {
            "research_data": new_research_data,
            "trace_history": [trace],
        }

    except Exception as e:
        logger.error(f"QueryGenerator execution failed: {str(e)}", exc_info=True)
        trace = build_trace(
            "query_generator",
            "FAIL",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"error": str(e)}
        )
        return {"trace_history": [trace]}

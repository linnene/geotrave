"""
Module: src.agent.nodes.analyst.node
Responsibility: Extracts requirements and updates UserProfile.
Determines if mandatory fields are complete to proceed with research.
Parent Module: src.agent.nodes
Dependencies: langchain_core, src.agent.state, src.utils
"""

import time
import json
from typing import Dict, Any

from src.agent.state import TravelState, AnalystOutput, ExecutionSigns
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import analyst_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history
from .config import TEMPERATURE, HISTORY_LIMIT, MAX_TOKENS

logger = get_logger("AnalystNode")


def _get_format_instructions() -> str:
    """Extracts and formats the JSON schema from AnalystOutput for LLM guidance."""
    return json.dumps(AnalystOutput.model_json_schema(), indent=2, ensure_ascii=False)


async def analyst_node(state: TravelState) -> Dict[str, Any]:
    """
    Requirement Analyst Node.
    Parses conversation history to build a structured UserProfile.
    """
    start_time = time.time()
    logger.info("Processing requirement extraction at [Analyst]...")

#========================================================

    # 1. Prepare Context
    messages = state.get("messages", [])
    last_user_msg = messages[-1].content if messages else ""

    # 使用解耦的历史格式化工具
    history = format_recent_history(messages, HISTORY_LIMIT)
    current_profile_json = state.get("user_profile").model_dump_json(indent=2) if state.get("user_profile") else "{}"

    # 2. LLM Orchestration
    prompt_str = analyst_prompt_template.format(
        current_profile=current_profile_json,
        history=history,
        user_input=last_user_msg,
        format_instructions=_get_format_instructions()
    )

    llm = LLMFactory.get_model("Analyst", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    # Using json_object mode for robust compatibility with DeepSeek/OpenAI
    bound_llm = llm.bind(response_format={"type": "json_object"})

#========================================================

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        
        # Manual parse from JSON string
        content = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
        
        # Handle cases where content might be a list (multimodal or complex tool outputs)
        if isinstance(content, list):
            # Find the first text block or join them
            content_str = ""
            for item in content:
                if isinstance(item, str):
                    content_str += item
                elif isinstance(item, dict) and item.get("type") == "text":
                    content_str += item.get("text", "")
        else:
            content_str = str(content)

        parsed_json = json.loads(content_str)
        result = AnalystOutput(**parsed_json)
        
        # 4. Critical Fields Audit (Centralized Logic in schema.py)
        # is_core_complete: 是否达到了开启 Manager 的门槛
        # all_missing: UserProfile 中所有尚未填写的字段，传给 Reply 节点
        is_core_complete, all_missing = result.updated_profile.check_completeness()
        
        logger.info(f"Analyst Audit: CoreComplete={is_core_complete}, TotalMissing={len(all_missing)}")
    except Exception as e:
        logger.error(f"Analyst execution failed: {str(e)}", exc_info=True)
        # Fallback to existing profile if extraction fails
        return {
            "trace_history": [build_trace(
                "analyst",
                "FAIL",
                latency_ms=int((time.time() - start_time) * 1000),
                detail={"error": str(e)}
            )]
        }

#========================================================

    # 5. Audit & State Assembly
    # Logic: 
    # - Node only provides facts via ExecutionSigns.
    # - Graph router will decide whether to wake up 'reply' and 'manager'.

    token_usage = {}
    if hasattr(raw_result, "response_metadata"):
        metadata = getattr(raw_result, "response_metadata", {})
        usage = metadata.get("token_usage", {})
        if usage:
            token_usage = {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0)
            }

    trace = build_trace(
        "analyst",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "is_core_complete": is_core_complete,
            "all_missing": all_missing,
            "reason": result.reason
        },
        token_usage=token_usage
    )

    return {
        "user_profile": result.updated_profile,
        "user_request": result.user_request,
        "missing_fields": all_missing, # Transmission of all missing fields to 'reply' node
        "execution_signs": (state.get("execution_signs") or ExecutionSigns()).model_copy(update={"is_core_complete": is_core_complete}),
        "trace_history": [trace]
    }

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

from src.agent.state import TraceLog, TravelState, AnalystOutput
from utils.llm_factory import LLMFactory
from utils.prompt import analyst_prompt_template
from utils.logger import get_logger

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
    # Filter only recent Human/AI messages to avoid context bloat (N=10)
    history = "\n".join([f"{m.type}: {m.content}" for m in messages[-11:-1]])
    current_profile_json = state.get("user_profile").model_dump_json(indent=2) if state.get("user_profile") else "{}"

    # 2. LLM Orchestration
    prompt_str = analyst_prompt_template.format(
        current_profile=current_profile_json,
        history=history,
        user_input=last_user_msg,
        format_instructions=_get_format_instructions()
    )

    llm = LLMFactory.get_model("analyst", temperature=0)
    # Using json_object mode for robust compatibility with DeepSeek/OpenAI
    bound_llm = llm.bind(response_format={"type": "json_object"})

#========================================================

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        
        # Manual parse from JSON string
        content_str = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
        parsed_json = json.loads(content_str)
        result = AnalystOutput(**parsed_json)
        
        logger.info(f"Analyst Extraction: Complete={result.is_complete}. Reason: {result.reason}")
    except Exception as e:
        logger.error(f"Analyst execution failed: {str(e)}", exc_info=True)
        # Fallback to existing profile if extraction fails
        return {
            "trace_history": [TraceLog(
                node="analyst",
                status="FAIL",
                latency_ms=int((time.time() - start_time) * 1000),
                detail={"error": str(e)}
            )]
        }

#========================================================

    # 3. Audit & State Assembly
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

    trace = TraceLog(
        node="analyst",
        status="SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "is_complete": result.is_complete,
            "missing": result.missing_fields,
            "reason": result.reason
        },
        token_usage=token_usage
    )

#========================================================


    return {
        "user_profile": result.updated_profile,
        "user_request": result.user_request,
        "trace_history": [trace]
    }

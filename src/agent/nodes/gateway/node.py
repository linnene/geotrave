"""
Module: src.agent.nodes.gateway.node
Responsibility: Executes security filtering and intent classification. 
Acts as the entry node of the TravelGraph to ensure request validity.
Parent Module: src.agent.nodes
Dependencies: langchain_core, src.agent.state, src.utils
"""

import time
import json
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from src.agent.state import RouteMetadata, TraceLog, TravelState, GatewayOutput
from utils.llm_factory import LLMFactory
from utils.prompt import gateway_prompt_template
from utils.logger import get_logger

logger = get_logger("GatewayNode")


def _get_format_instructions() -> str:
    """Extracts and formats the JSON schema from GatewayOutput for LLM guidance."""
    return json.dumps(GatewayOutput.model_json_schema(), indent=2, ensure_ascii=False)


async def gateway_node(state: TravelState) -> Dict[str, Any]:
    """
    Entry gate for the LangGraph workflow.
    Validates user intent against GeoTrave's business scope and security policies.
    """
    start_time = time.time()
    logger.info("Processing entry request at [Gateway]...")

#========================================================

    # 1. Extract context
    messages = state.get("messages", [])
    if not messages:
        logger.warning("Empty message state detected in GatewayNode.")
        return {"needs_exit": True}
    
    last_user_msg = messages[-1].content
    
    # 2. LLM Orchestration with dynamic schema injection
    prompt_str = gateway_prompt_template.format(
        user_input=last_user_msg,
        format_instructions=_get_format_instructions()
    )
    
    llm = LLMFactory.get_model("gateway", temperature=0)
    # Use bind with json_object for better compatibility with providers like DeepSeek
    # instead of with_structured_output(GatewayOutput) which uses tool_calling/json_schema.
    bound_llm = llm.bind(response_format={"type": "json_object"})

#========================================================

    try:
        # 3. LLM Reasoning
        raw_result = await bound_llm.ainvoke(prompt_str)
        
        # Manual parse from JSON string in AIMessage content
        import json as json_lib
        content_str = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
        parsed_json = json_lib.loads(content_str)
        result = GatewayOutput(**parsed_json)
        
        is_valid = result.is_valid
        reason = result.reason
        reply = result.reply
        category = result.category
        
        logger.info(f"Gateway Verdict: {category.upper()} | Valid: {is_valid}")
    except Exception as e:
        logger.error(f"Gateway execution failed: {str(e)}", exc_info=True)
        is_valid, reason, category = False, f"System Error: {str(e)}", "system_error"
        reply = "系统安全网关暂时繁忙，请稍后再试。"

#========================================================

    # 3. Routing & Audit Assembly
    route = RouteMetadata(
        next_node="manager" if is_valid else "__end__",
        reason=f"[{category}] {reason}",
        is_error=not is_valid
    )

    # Extract token usage if available from LLM response
    token_usage = {}
    # Use cast or check with getattr to satisfy Pylance when result is potentially a dict or BaseMessage
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
        node="gateway",
        status="SUCCESS" if is_valid else ("REJECTED" if category in ["malicious", "chitchat"] else "FAIL"),
        latency_ms=int((time.time() - start_time) * 1000),
        detail={"category": category, "reason": reason},
        token_usage=token_usage
    )
    
#========================================================

    # 4. Prepare response state (with PII sanitization support)
    # If PII was sanitized, overwrite the last message to protect downstream nodes
    response_msg = []
    if is_valid:
        if result.sanitized_text:
            logger.info("PII detected and sanitized in Gateway.")
            response_msg = [HumanMessage(content=result.sanitized_text)]
    else:
        if reply:
            response_msg = [HumanMessage(content=reply)]

#========================================================

    return {
        "route_metadata": route,
        "trace_history": [trace],
        "needs_exit": not is_valid,
        "messages": response_msg
    }
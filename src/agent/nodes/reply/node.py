"""
Module: src.agent.nodes.reply.node
Responsibility: Generates natural language responses to guide the user when information is missing.
Parent Module: src.agent.nodes
Dependencies: langchain_core, src.agent.state, src.utils
"""

import time
from typing import Dict, Any

from langchain_core.messages import AIMessage
from src.agent.state import TraceLog, TravelState
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import reply_prompt_template
from src.utils.logger import get_logger
from .config import TEMPERATURE, MAX_TOKENS

logger = get_logger("ReplyNode")

async def reply_node(state: TravelState) -> Dict[str, Any]:
    """
    Reply Node.
    Generates a follow-up question based on missing_fields in the state.
    """
    start_time = time.time()
    logger.info("Generating follow-up response at [Reply]...")

    # 1. Prepare Context
    missing_fields = state.get("missing_fields", [])
    current_profile = state.get("user_profile")
    user_request = state.get("user_request", "")
    messages = state.get("messages", [])
    
    # Extract the last user message specifically to give Reply node "eyes"
    last_user_msg = ""
    for m in reversed(messages):
        if m.type == "human":
            last_user_msg = m.content
            break
    
    current_profile_json = current_profile.model_dump_json(indent=2) if current_profile else "{}"

    # 2. LLM Orchestration
    prompt_str = reply_prompt_template.format(
        last_user_message=last_user_msg,
        user_request=user_request,
        current_profile=current_profile_json,
        missing_fields=", ".join(missing_fields) if missing_fields else "全量信息已具备，正在深化细节"
    )

    llm = LLMFactory.get_model("Reply", temperature=TEMPERATURE, max_tokens=MAX_TOKENS) 
    
    try:
        response = await llm.ainvoke(prompt_str)
        reply_text = response.content if hasattr(response, "content") else str(response)
        
        # Clean up in case LLM ignored "no JSON" instructions
        if isinstance(reply_text, list): # Handle multimodal content
            reply_text = "".join([i.get("text", "") if isinstance(i, dict) else str(i) for i in reply_text])
            
    except Exception as e:
        logger.error(f"Reply generation failed: {str(e)}", exc_info=True)
        reply_text = "我还需要了解更多关于您旅行意图的信息，比如目的地或天数。您可以详细说说吗？"

    logger.debug(f"Generated reply: {reply_text}...")

    # 3. Audit & State Assembly
    trace = TraceLog(
        node="reply",
        status="SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "missing_fields": missing_fields,
            "generated_reply_preview": reply_text[:50] + "..."
        }
    )

    output = {
        "messages": [AIMessage(content=reply_text)],
        "trace_history": [trace]
    }

    return output

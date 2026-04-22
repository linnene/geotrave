"""
Module: src.agent.nodes.gateway.node
Responsibility: Security filtering, intent classification, and early exit signaling via structured LLM output.
"""

import time
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from src.agent.state import RouteMetadata, TraceLog, TravelState, GatewayOutput
from utils.llm_factory import LLMFactory
from utils.prompt import gateway_prompt_template
from utils.logger import get_logger

logger = get_logger("GatewayNode")


async def gateway_node(state: TravelState) -> Dict[str, Any]:
    """
    网关节点处理函数：
    - 作为图的入口节点识别意图。
    - 使用 structured_output 强制约束输出模型。
    - 生成 TraceLog 与 RouteMetadata。
    """
    start_time = time.time()
    logger.info("Enter [Gateway] node.")
    
    # 1. 提取上下文信息
    messages = state.get("messages", [])
    if not messages:
        logger.debug("No messages found in state.")
        return {"needs_exit": True}
    
    last_user_msg = messages[-1].content
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[:-1]]) if len(messages) > 1 else "无历史记录"
    
    logger.debug(f"Handling user input: '{last_user_msg[:50]}...'")

    # 2. 准备 Prompt 与 LLM
    prompt_str = gateway_prompt_template.format(history=history_str, user_input=last_user_msg)
    llm = LLMFactory.get_model("gateway", temperature=0)
    structured_llm = llm.with_structured_output(GatewayOutput)
    
    try:
        logger.debug("Calling Gateway LLM with structured output...")
        result: GatewayOutput = await structured_llm.ainvoke(prompt_str)
        
        is_valid = result.is_valid
        reason = result.reason
        reply = result.reply
        category = result.category
        
        logger.info(f"Gateway verdict: {category.upper()} (valid={is_valid}). Reason: {reason}")
    except Exception as e:
        logger.error(f"Gateway LLM logic failed: {e}", exc_info=True)
        is_valid = False
        reason = f"Gateway LLM execution error: {str(e)}"
        reply = "系统安全网关暂时繁忙，请稍后再试。"
        category = "system_error"

    # 3. 状态路由与装配
    route = RouteMetadata(
        next_node="manager" if is_valid else "__end__",
        reason=f"[{category}] {reason}",
        is_error=not is_valid
    )
    
    trace_status = "SUCCESS" if is_valid else ("REJECTED" if category in ["malicious", "chitchat"] else "FAIL")
    trace = TraceLog(
        node="gateway",
        status=trace_status,
        latency_ms=int((time.time() - start_time) * 1000),
        detail={"category": category, "reason": reason},
        token_usage={}
    )
    
    return {
        "route_metadata": route,
        "trace_history": [trace],
        "needs_exit": not is_valid,
        "messages": [HumanMessage(content=reply)] if not is_valid and reply else []
    }
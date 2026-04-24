"""
Module: src.agent.nodes.manager.node
Responsibility: Acts as the Brain/Router of the Agent. 
Decides the next global stage (Loop, Recommender, Planner, or Reply) 
based on execution signs and research manifests.
"""

import time
from typing import Dict, Any

from src.agent.state import TravelState, RouteMetadata, TraceLog, ManagerOutput
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import manager_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils.history_tools import format_recent_history, format_trace_history
from .config import TEMPERATURE, MAX_TOKENS, HISTORY_LIMIT, NODE_HISTORY_LIMIT

from langchain_core.output_parsers import JsonOutputParser

logger = get_logger("ManagerNode")

# 使用 JsonOutputParser 来获取更紧凑的指令
parser = JsonOutputParser(pydantic_object=ManagerOutput)

async def manager_node(state: TravelState) -> Dict[str, Any]:
    """
    Manager Node - The LLM-driven orchestrator.
    Decides the next global stage based on evidence from other nodes.
    """
    start_time = time.time()
    logger.info("Manager - Thinking about the next strategic step...")

    # 1. Prepare Context (Evidence-based)
    signs = state.get("execution_signs")
    research_manifest = state.get("research_data")
    messages = state.get("messages", [])
    
    is_safe = signs.is_safe if signs else True
    is_core_complete = signs.is_core_complete if signs else False
    hashes_count = len(research_manifest.verified_results) if research_manifest else 0
    
    history = format_recent_history(messages, HISTORY_LIMIT) # 简短历史参考
    user_request = state.get("user_request", "未知诉求")
    
    # 获取并格式化流转历史
    trace_logs = state.get("trace_history", [])
    trace_history_str = format_trace_history(trace_logs, 5)

    # 2. LLM Orchestration
    prompt_str = manager_prompt_template.format(
        is_safe=is_safe,
        is_core_complete=is_core_complete,
        hashes_count=hashes_count,
        history=history,
        user_request=user_request,
        trace_history=trace_history_str,
        format_instructions=parser.get_format_instructions()
    )

    llm = LLMFactory.get_model("manager", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        # 使用 parser 来处理结果，更鲁棒
        chain = llm | parser
        decision = await chain.ainvoke(prompt_str)
        
        next_node = decision.get("next_stage")
        reason = decision.get("rationale", "无具体理由")
        
        logger.info(f"Manager Decision: -> {next_node.upper()} | Reason: {reason}")
    except Exception as e:
        logger.error(f"Manager reasoning failed: {str(e)}", exc_info=True)
        # Fallback to safe logic if LLM fails
        next_node = "reply" if not is_core_complete else "query_generator"
        reason = f"Fallback due to error: {str(e)}"

    # 3. Issue Routing Command
    route = RouteMetadata(
        next_node=next_node,
        reason=reason,
        is_error=False
    )

    trace = TraceLog(
        node="manager",
        status="SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "decision": next_node,
            "reason": reason,
            "hashes_count": hashes_count
        }
    )

    return {
        "route_metadata": route,
        "trace_history": [trace]
    }

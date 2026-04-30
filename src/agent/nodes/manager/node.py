"""
Module: src.agent.nodes.manager.node
Responsibility: Acts as the Brain/Router of the Agent. 
Decides the next global stage (Loop, Recommender, Planner, or Reply) 
based on execution signs and research manifests.
"""

import time
from typing import Dict, Any

from src.agent.state import TravelState, RouteMetadata, ManagerOutput
from src.agent.state.schema import ResearchLoopInternal
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import manager_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, format_recent_history, format_trace_history
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
    research_hashes = research_manifest.research_hashes if research_manifest else {}
    hashes_count = sum(len(v) for v in research_hashes.values())
    research_history = research_manifest.research_history if research_manifest else []

    history = format_recent_history(messages, HISTORY_LIMIT)
    user_request = state.get("user_request", "未知诉求")

    # 获取并格式化流转历史
    trace_logs = state.get("trace_history", [])
    trace_history_str = format_trace_history(trace_logs, 5)

    # 调研新鲜度：当前 user_request 是否已有对应的调研记录
    research_matches_current = (
        research_history[-1] == user_request
        if research_history
        else False
    )

    # 2. LLM Orchestration
    prompt_str = manager_prompt_template.format(
        is_safe=is_safe,
        is_core_complete=is_core_complete,
        hashes_count=hashes_count,
        research_matches_current=research_matches_current,
        research_history=research_history if research_history else "[]",
        history=history,
        user_request=user_request,
        trace_history=trace_history_str,
        format_instructions=parser.get_format_instructions()
    )

    llm = LLMFactory.get_model("Manager", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        # 使用 parser 来处理结果，更鲁棒
        chain = llm | parser
        decision = await chain.ainvoke(prompt_str)
        
        next_node = decision.get("next_stage")
        reason = decision.get("rationale", "无具体理由")

        logger.info(f"Manager Decision: -> {next_node.upper()} | Reason: {reason}")
    except Exception as e:
        logger.error(f"Manager reasoning failed: {str(e)}", exc_info=True)
        next_node = "reply" if not is_core_complete else "research_loop"
        reason = f"Fallback due to error: {str(e)}"

    # 硬守卫: is_core_complete=False 时必须导向 reply，防止 LLM 输出自相矛盾
    if not is_core_complete and next_node != "reply":
        logger.warning(
            f"Manager override: is_core_complete=False, forcing reply (was: {next_node})"
        )
        reason = f"[硬守卫覆写] is_core_complete 为 False，强制导向 reply。原决策: {next_node}，原理由: {reason}"
        next_node = "reply"

    # 3. Issue Routing Command
    route = RouteMetadata(
        next_node=next_node,
        reason=reason,
        is_error=False
    )

    trace = build_trace(
        "manager",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "decision": next_node,
            "reason": reason,
            "hashes_count": hashes_count,
            "research_history": research_history[-3:],
        }
    )

    result: Dict[str, Any] = {
        "route_metadata": route,
        "trace_history": [trace],
    }

    # 路由到 research_loop 时重置其内部状态，防止上一次循环的 feedback/passed_queries 污染本轮
    if next_node == "research_loop" and research_manifest:
        result["research_data"] = research_manifest.model_copy(
            update={"loop_state": ResearchLoopInternal()}
        )

    return result

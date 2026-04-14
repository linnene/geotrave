#Researcher Node: Decoupled Researcher Node using ResearcherTools for multi-dimensional retrieval

import asyncio
from agent.nodes.researcher.tools import ResearcherTools
from agent.state import TravelState
from utils.logger import logger
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from utils.config import (
    RESEARCHER_MODEL_ID,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_API_KEY,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

# 使用配置中特定的 Researcher 模型
researcher_llm = ChatOpenAI(
    model=RESEARCHER_MODEL_ID,
    api_key=SecretStr(RESEARCHER_MODEL_API_KEY), 
    base_url=RESEARCHER_MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,
    disable_streaming=True,
)


async def researcher_node(state: TravelState):
    """
    检索节点：解耦后的研究员节点，使用独立模型配置。
    重构为完全异步并发模型，使用 scatter/gather 并发拉取网络与本地结果。
    """
    core_req = state.get("user_profile") or {}
    destination = core_req.get("destination")
    if not destination:
        logger.debug("[Researcher Node] No destination provided, retrieval skipped.")
        return {
            "search_data": {
                "query_history": [],
                "retrieval_context": "No destination provided, retrieval skipped.",
                "retrieval_results": []
            }
        }

    logger.info(f"[Researcher Node] Start async research for: {destination}")

    # 1. 产生检索计划 (传递特定 LLM)
    plan = await ResearcherTools.generate_research_plan(state, researcher_llm) # type: ignore
    
    tasks = []
    
    if not plan:
        # 如果计划生成失败，进行基础检索降级
        fallback_query = ",".join(destination) if isinstance(destination, list) else str(destination)
        tasks.append(ResearcherTools.search_local_kt(fallback_query))
    else:
        # 2. 从本地知识库检索任务
        if plan.local_query:
            tasks.append(ResearcherTools.search_local_kt(plan.local_query))

        # 3. 网络搜索任务 (并发撒网)
        if plan.web_queries:
            for q in plan.web_queries:
                tasks.append(ResearcherTools.search_web_ddg(query=q, max_results=10))

    # 并发执行所有检索任务
    logger.debug(f"[Researcher Node] Concurrently executing {len(tasks)} retrieval tasks...")
    gathered_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 压平并过滤结果
    all_results = []
    for res in gathered_results:
        if isinstance(res, Exception):
            logger.error(f"[Researcher Node] A retrieval task failed: {res}")
            continue
        if isinstance(res, list):
            all_results.extend(res)

    # 4. 汇总 (为了向下兼容 Planner 节点)
    context_parts = []
    
    if not all_results:
        logger.debug("[Researcher Node] Empty results. Return with needs_research reset.")
        return {
            "needs_research": False,
            "search_data": {
                "query_history": plan.web_queries if plan else [],
                "retrieval_context": "No relevant information found.",
                "retrieval_results": []
            }
        }
        
    for item in all_results:
        # 因为 item 现在是 TypedDict (即字典)，需要用类似 item["source"] 的方式取值
        source_val = item.get("source", "unknown").upper() if isinstance(item, dict) else getattr(item, "source", "unknown").upper()
        title_val = item.get("title", "No Title") if isinstance(item, dict) else getattr(item, "title", "No Title")
        content_val = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
        link_val = item.get("link") if isinstance(item, dict) else getattr(item, "link", None)
        
        part = f"[{source_val}] {title_val}\n{content_val}"
        if link_val and link_val != "#":
            part += f"\nSource: {link_val}"
        context_parts.append(part)
    
    final_context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found."
    
    return {
        "needs_research": False,  # 检索完毕后重置标志位，避免状态树遗留被后续节点误用
        "search_data": {
            "query_history": plan.web_queries if plan else [],
            "retrieval_context": final_context,
            "retrieval_results": all_results
        }
    }

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
        yield {
            "search_data": {
                "query_history": [],
                "retrieval_context": "No destination provided, retrieval skipped.",
                "retrieval_results": [],
                "retrieval_stats": {"total_fetched": 0, "total_filtered": 0, "valid_count": 0}
            }
        }
        return

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

    # 并发执行所有检索任务，使用 as_completed 使得哪条检索先完成就先写入哪条
    logger.debug(f"[Researcher Node] Concurrently executing {len(tasks)} retrieval tasks...")
    
    all_results = []
    plan_web_queries = plan.web_queries if plan else []
    
    total_fetched = 0
    total_filtered = 0

    # 遍历只要有任何一个 task 完成就立即处理并 yield 出来 (流式写入)
    for completed_task in asyncio.as_completed(tasks):
        try:
            res = await completed_task
            if isinstance(res, list):
                # 新增二级 LLM 过滤（质检员环节），剥离无关水分杂讯
                if len(res) > 0:
                    total_fetched += len(res)
                    filtered_res = await ResearcherTools.filter_retrieval_items(res, researcher_llm)
                    total_filtered += (len(res) - len(filtered_res))
                    all_results.extend(filtered_res)
            
            # 构建中间累加的文本
            context_parts = []
            for item in all_results:
                source_val = item.get("source", "unknown").upper() if isinstance(item, dict) else getattr(item, "source", "unknown").upper()
                title_val = item.get("title", "No Title") if isinstance(item, dict) else getattr(item, "title", "No Title")
                content_val = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
                link_val = item.get("link") if isinstance(item, dict) else getattr(item, "link", None)
                
                part = f"[{source_val}] {title_val}\n{content_val}"
                if link_val and link_val != "#":
                    part += f"\nSource: {link_val}"
                context_parts.append(part)

            final_context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found."
            
            # 流式递增 Yield 当前收集到的总进度
            yield {
                "needs_research": False,
                "search_data": {
                    "query_history": plan_web_queries,
                    "retrieval_context": final_context,
                    "retrieval_results": all_results.copy(),
                    "retrieval_stats": {
                        "total_fetched": total_fetched,
                        "total_filtered": total_filtered,
                        "valid_count": len(all_results)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[Researcher Node] A retrieval task failed: {e}")
            continue

    if not all_results:
        logger.debug("[Researcher Node] Empty results. Return with needs_research reset.")
        yield {
            "needs_research": False,
            "search_data": {
                "query_history": plan_web_queries,
                "retrieval_context": "No relevant information found.",
                "retrieval_results": [],
                "retrieval_stats": {
                    "total_fetched": total_fetched,
                    "total_filtered": total_filtered,
                    "valid_count": len(all_results)
                }
            }
        }

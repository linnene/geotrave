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

        # 4. 天气外部 API 拉取
        if plan.need_weather:
            # 获取用户设置的日期范围
            date_range = core_req.get("date")  # [None, None] or ["2026-04-20", "2026-04-25"]
            s_date, e_date = None, None
            if date_range and len(date_range) == 2:
                s_date, e_date = date_range[0], date_range[1]

            # 针对所有目的地拉取天气
            dests = destination if isinstance(destination, list) else [destination]
            for dest in dests:
                tasks.append(ResearcherTools.search_weather_openmeteo(
                    location=dest, 
                    start_date=s_date, 
                    end_date=e_date
                ))

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
                # 如果是天气 API 返回的结果，我们需要特殊处理
                weather_items = [item for item in res if (isinstance(item, dict) and item.get("source") == "api_weather") or (hasattr(item, "source") and getattr(item, "source") == "api_weather")]
                other_items = [item for item in res if item not in weather_items]

                # 处理非天气结果：二级 LLM 过滤
                if other_items:
                    total_fetched += len(other_items)
                    filtered_res = await ResearcherTools.filter_retrieval_items(other_items, researcher_llm)
                    total_filtered += (len(other_items) - len(filtered_res))
                    all_results.extend(filtered_res)
                
                # 处理天气结果：直接汇总到专门的字段，不进入 all_results 进行通用拼接
                current_weather_info = state.get("search_data", {}).get("weather_info") or ""
                if weather_items:
                    for w in weather_items:
                        w_content = w.get("content", "") if isinstance(w, dict) else getattr(w, "content", "")
                        w_title = w.get("title", "") if isinstance(w, dict) else getattr(w, "title", "")
                        current_weather_info += f"### {w_title}\n{w_content}\n\n"
            
            # 构建中间累加的文本 (排除天气，因为天气已经单开了频道)
            context_parts = []
            for item in all_results:
                source_val = item.get("source", "unknown").upper() if isinstance(item, dict) else getattr(item, "source", "unknown").upper()
                if source_val == "API_WEATHER": continue # 再次防御性检查，确保不混入 context

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
                    "weather_info": current_weather_info if current_weather_info else None,
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

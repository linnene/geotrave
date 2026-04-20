"""
Module: src.agent.nodes.researcher.researcher
Responsibility: Performs multi-dimensional asynchronous research (local RAG, web, weather) and sanitizes results.
Parent Module: src.agent.nodes.researcher
Dependencies: asyncio, langchain_openai, src.agent.state, src.utils, researcher.tools

Refactoring Standard: Full async concurrency with stream-like generator updates, centralized LLM factory.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any

from src.agent.nodes.researcher.tools import ResearcherTools
from src.agent.state import TravelState
from src.utils import logger, LLMFactory

# 1. Init Researcher's LLM via Factory
researcher_llm = LLMFactory.get_model("researcher")


async def researcher_node(state: TravelState) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Decoupled researcher node using an independent model configuration.
    Implements scatter/gather concurrency to fetch both web and local results.
    
    Args:
        state (TravelState): Current graph state.
        
    Yields:
        Dict[str, Any]: Incremental search_data updates.
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

    # 1. Generate Research Plan
    plan = await ResearcherTools.generate_research_plan(state, researcher_llm)
    
    tasks = []
    
    if not plan:
        fallback_query = ",".join(destination) if isinstance(destination, list) else str(destination)
        tasks.append(ResearcherTools.search_local_kt(fallback_query))
    else:
        # 2. Local RAG Tasks
        if plan.local_query:
            tasks.append(ResearcherTools.search_local_kt(plan.local_query))

        # 3. Web Search Tasks (Concurrent)
        if plan.web_queries:
            for q in plan.web_queries:
                tasks.append(ResearcherTools.search_web_ddg(query=q, max_results=10))

        # 4. Weather API Tasks
        if plan.need_weather:
            date_range = core_req.get("date")
            s_date, e_date = None, None
            if date_range and len(date_range) == 2:
                s_date, e_date = date_range[0], date_range[1]

            dests = destination if isinstance(destination, list) else [destination]
            for dest in dests:
                tasks.append(ResearcherTools.search_weather_openmeteo(
                    location=dest, 
                    start_date=s_date, 
                    end_date=e_date
                ))

    logger.debug(f"[Researcher Node] Concurrently executing {len(tasks)} retrieval tasks...")
    
    all_results = []
    plan_web_queries = plan.web_queries if plan else []
    current_weather_info = ""
    
    total_fetched = 0
    total_filtered = 0

    # Process tasks as they complete for incremental state updates
    for completed_task in asyncio.as_completed(tasks):
        try:
            res = await completed_task
            if isinstance(res, list):
                # Separate weather from other items
                weather_items = [item for item in res if (isinstance(item, dict) and item.get("source") == "api_weather") or (hasattr(item, "source") and getattr(item, "source") == "api_weather")]
                other_items = [item for item in res if item not in weather_items]

                # Secondary LLM sanitization for non-weather results
                if other_items:
                    total_fetched += len(other_items)
                    filtered_res = await ResearcherTools.filter_retrieval_items(other_items, researcher_llm)
                    total_filtered += (len(other_items) - len(filtered_res))
                    all_results.extend(filtered_res)
                
                # Format and accumulate weather info
                if weather_items:
                    for w in weather_items:
                        w_content = w.get("content", "") if isinstance(w, dict) else getattr(w, "content", "")
                        w_title = w.get("title", "") if isinstance(w, dict) else getattr(w, "title", "")
                        current_weather_info += f"### {w_title}\n{w_content}\n\n"
            
            # Aggregate textual context
            context_parts = []
            for item in all_results:
                source_val = item.get("source", "unknown").upper() if isinstance(item, dict) else getattr(item, "source", "unknown").upper()
                if source_val == "API_WEATHER": continue

                title_val = item.get("title", "No Title") if isinstance(item, dict) else getattr(item, "title", "No Title")
                content_val = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
                link_val = item.get("link") if isinstance(item, dict) else getattr(item, "link", None)
                
                part = f"[{source_val}] {title_val}\n{content_val}"
                if link_val and link_val != "#":
                    part += f"\nSource: {link_val}"
                context_parts.append(part)

            final_context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant information found."
            
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
                    "valid_count": 0
                }
            }
        }

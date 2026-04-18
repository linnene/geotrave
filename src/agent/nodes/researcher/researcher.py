"""
Researcher Node: Multi-dimensional retrieval orchestrated by LLM-guided tools.

This node performs concurrent retrieval across web, vector DB, and weather APIs.

Parent Module: src.agent.nodes
Dependencies: agent.factory, agent.state, .tools
"""

import asyncio
from agent.nodes.researcher.tools import ResearcherTools
from agent.state import TravelState
from agent.factory import LLMFactory
from utils.logger import logger

# Initialize Researcher's LLM using the factory
researcher_llm = LLMFactory.create_researcher_llm()

async def researcher_node(state: TravelState):
    """
    Orchestrate multi-source retrieval (Web, local RAG, Weather).
    
    This node concurrently executes retrieval tasks and yields partial states
    for a streaming user experience.
    """
    core_req = state.get("user_profile") or {}
    destination = core_req.get("destination")
    
    if not destination:
        logger.debug("[Researcher Node] No destination provided, skipping retrieval.")
        yield {
            "search_data": {
                "query_history": [],
                "retrieval_context": "No destination provided.",
                "retrieval_results": [],
                "retrieval_stats": {"total_fetched": 0, "total_filtered": 0, "valid_count": 0}
            }
        }
        return

    logger.info(f"[Researcher Node] Starting async retrieval for: {destination}")

    # 1. Generate structured research plan
    plan = await ResearcherTools.generate_research_plan(state, researcher_llm) # type: ignore
    
    tasks = []
    
    if not plan:
        # Fallback to basic search if plan generation fails
        fallback_query = ",".join(destination) if isinstance(destination, list) else str(destination)
        tasks.append(ResearcherTools.search_local_kt(fallback_query))
    else:
        # 2. Local Knowledge Base Task
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

    # Concurrently execute and yield partial results for streaming
    logger.debug(f"[Researcher Node] Executing {len(tasks)} parallel tasks...")
    
    all_results = []
    plan_web_queries = plan.web_queries if plan else []
    total_fetched = 0
    total_filtered = 0
    current_weather_info = state.get("search_data", {}).get("weather_info") or ""

    for completed_task in asyncio.as_completed(tasks):
        try:
            res = await completed_task
            if not isinstance(res, list):
                continue

            # Separate weather items from general results
            weather_items = [
                item for item in res 
                if (isinstance(item, dict) and item.get("source") == "api_weather") or 
                   (hasattr(item, "source") and getattr(item, "source") == "api_weather")
            ]
            other_items = [item for item in res if item not in weather_items]

            # Process general items with LLM filtering
            if other_items:
                total_fetched += len(other_items)
                filtered_res = await ResearcherTools.filter_retrieval_items(other_items, researcher_llm)
                total_filtered += (len(other_items) - len(filtered_res))
                all_results.extend(filtered_res)
            
            # Update dedicated weather channel
            if weather_items:
                for w in weather_items:
                    w_content = w.get("content", "") if isinstance(w, dict) else getattr(w, "content", "")
                    w_title = w.get("title", "") if isinstance(w, dict) else getattr(w, "title", "")
                    current_weather_info += f"### {w_title}\n{w_content}\n\n"
            
            # Aggregate context for LLM consumption (excluding weather)
            context_parts = []
            for item in all_results:
                source = (item.get("source", "unknown") if isinstance(item, dict) else getattr(item, "source", "unknown")).upper()
                if source == "API_WEATHER":
                    continue

                title = item.get("title", "No Title") if isinstance(item, dict) else getattr(item, "title", "No Title")
                content = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
                link = item.get("link") if isinstance(item, dict) else getattr(item, "link", None)
                
                entry = f"[{source}] {title}\n{content}"
                if link and link != "#":
                    entry += f"\nSource: {link}"
                context_parts.append(entry)

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
            logger.error(f"[Researcher Node] Task error: {e}")
            continue

    if not all_results and not current_weather_info:
        logger.debug("[Researcher Node] No results found.")
        yield {
            "needs_research": False,
            "search_data": {
                "query_history": plan_web_queries,
                "retrieval_context": "No relevant information found.",
                "retrieval_results": [],
                "weather_info": None,
                "retrieval_stats": {
                    "total_fetched": total_fetched,
                    "total_filtered": total_filtered,
                    "valid_count": 0
                }
            }
        }

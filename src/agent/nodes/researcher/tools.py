"""
Module: src.agent.nodes.researcher.tools
Responsibility: Provides decoupled external API toolsets (RAG, Web Search, Weather) for the Researcher node.
Parent Module: src.agent.nodes.researcher
Dependencies: asyncio, urllib, json, ddgs, langchain_openai, src.database.vector_db, src.utils, src.agent.state, src.agent.schema

Strictly implements asymmetric background tasks (`asyncio.to_thread` for legacy sync APIs) 
to ensure the main LangGraph event loop is never blocked by I/O bottlenecks.
"""

import asyncio
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, List, Any

# Top-level unified imports adhering to the robust import architecture
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from ddgs import DDGS

from src.database.vector_db import search_similar_documents
from src.utils import logger, research_query_prompt_template, research_filter_prompt_template
from src.agent.state import RetrievalItem
from src.agent.schema import ResearchPlan

class ResearcherTools:
    """
    Encapsulated toolset for the Researcher node.
    All methods are static and fully asynchronous.
    """
    
    @staticmethod
    async def generate_research_plan(state: Dict[str, Any], LLM: ChatOpenAI) -> Optional[ResearchPlan]:
        """
        Produce a structured research plan based on the current TravelState layout.
        
        Args:
            state (Dict[str, Any]): The current contextual graph state.
            LLM (ChatOpenAI): The language model instance provisioned for generation.
            
        Returns:
            Optional[ResearchPlan]: The extracted research plan, or None if conditions fail.
        """
        user_profile = state.get("user_profile") or {}
        destination = user_profile.get("destination")
        if not destination:
            return None
        
        parser = PydanticOutputParser(pydantic_object=ResearchPlan)
        
        # Extract the last 3 messages for immediate dense context
        messages = state.get("messages", [])
        recent_k_messages = messages[-3:] if len(messages) >= 3 else messages
        recent_context_str = "\n".join(
            [f"{msg.type}: {msg.content}" for msg in recent_k_messages]
        ) if recent_k_messages else "No recent context."
        
        prompt = research_query_prompt_template.format(
            destination=destination,
            days=user_profile.get("days"),
            people_count=user_profile.get("people_count"),
            date=user_profile.get("date"),
            budget_limit=user_profile.get("budget_limit") or 0,
            accommodation=user_profile.get("accommodation"),
            dining=user_profile.get("dining"),
            transportation=user_profile.get("transportation"),
            pace=user_profile.get("pace"),
            activities=user_profile.get("activities", []),
            preferences=user_profile.get("preferences", []),
            avoidances=user_profile.get("avoidances", []),
            recent_context=recent_context_str,
            format_instructions=parser.get_format_instructions()
        )
        
        try:
            logger.debug(f"[Researcher Tools] Thinking about research plan for: {destination}")
            response = await LLM.ainvoke(prompt)
            # Ensure content is string for Pydantic parser
            content_str = str(response.content) if not isinstance(response.content, str) else response.content
            plan = parser.parse(content_str)
            logger.debug(f"[Researcher Tools] Plan generated: {plan}")
            return plan
        except Exception as e:
            logger.error(f"[Researcher Tools] Plan generation failed: {str(e)}")
            dest_str = ",".join(destination) if isinstance(destination, list) else str(destination)
            # Graceful fallback logic matching exactly the original system behavior
            return ResearchPlan(
                local_query=dest_str,
                web_queries=[f"{dest_str} 旅游攻略"],
                need_weather=False,
                need_api=[]
            )

    @staticmethod
    async def search_local_kt(query: str, k: int = 3) -> List[RetrievalItem]:
        """
        Retrieve structured information asynchronously from the local ChromaDB vector store.
        
        Args:
            query (str): The search query.
            k (int): Number of top documents to fetch.
            
        Returns:
            List[RetrievalItem]: Mapped retrieval items representing knowledge base snippets.
        """
        try:
            logger.debug(f"[Researcher Tools] Local RAG search for: {query}")
            search_results = await search_similar_documents(query, k)
            
            items: List[RetrievalItem] = []
            for doc in search_results:
                items.append(RetrievalItem(
                    source="local",
                    link=None,
                    title="Knowledge Base Snippet",
                    content=getattr(doc, "page_content", str(doc)),
                    metadata={"query": query}
                ))
            return items
        except Exception as e:
            logger.error(f"[Researcher Tools] Local search failed: {str(e)}")
            return []

    @staticmethod
    async def filter_retrieval_items(items: List[RetrievalItem], LLM: ChatOpenAI) -> List[RetrievalItem]:
        """
        Secondary LLM-driven filtering mechanism to purge severely irrelevant search hits.
        
        Args:
            items (List[RetrievalItem]): The raw aggregated retrieval results.
            LLM (ChatOpenAI): LLM designated for evaluation.
            
        Returns:
            List[RetrievalItem]: The sanitized list of relevant items.
        """
        if not items:
            return []
            
        async def _check_single_item(item: RetrievalItem) -> Optional[RetrievalItem]:
            title = item.get("title", "") if isinstance(item, dict) else getattr(item, "title", "")
            content = item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")
            metadata = item.get("metadata", {}) if isinstance(item, dict) else getattr(item, "metadata", {})
            query = metadata.get("query", "提供背景信息")
            
            prompt = research_filter_prompt_template.format(
                query=query,
                title=title,
                content=content
            )
            try:
                res = await LLM.ainvoke(prompt)
                answer_raw = str(res.content).strip()
                answer = answer_raw.upper()
                if "NO" in answer and "YES" not in answer:
                    logger.debug(f"[Researcher Tools] Filter dropped irrelevant item: {title}")
                    return None
                else:
                    return item
            except Exception:
                # Retain item passively if LLM fails 
                return item

        # Dispatch concurrency
        tasks = [_check_single_item(item) for item in items]
        checked = await asyncio.gather(*tasks)
        return [raw for raw in checked if raw is not None]

    @staticmethod
    async def search_web_ddg(query: str, max_results: int = 10) -> List[RetrievalItem]:
        """
        Asynchronously perform DuckDuckGo web searches, isolating synchronous library calls.
        
        Args:
            query (str): The targeted search text.
            max_results (int): Threshold for return chunks.
            
        Returns:
            List[RetrievalItem]: Standardized web snippet items.
        """
        max_retries = 2
        timeout = 10
        
        def _sync_ddgs() -> List[Dict[str, str]]:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                with DDGS(timeout=timeout) as ddgs:
                    # Safely extract values from generator before exiting context
                    return list(ddgs.text(query, max_results=max_results, safesearch='on'))
                            
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"[Researcher Tools] Web search (DDG) for: {query} (Attempt {attempt + 1})")
                # 显式加入真正的异步超时管控，防止底层同步库彻底假死导致线程泄漏
                results = await asyncio.wait_for(asyncio.to_thread(_sync_ddgs), timeout=timeout + 2.0)

                if not results:
                    return []
                
                safety_blacklist = ["sex", "porn", "gamble", "赌博", "色情", "成人", "违禁"]
                
                formatted_items: List[RetrievalItem] = []
                for res in results:
                    title = res.get("title", "No Title")
                    snippet = res.get("body", "No Content")
                    link = res.get("href", "#")
                    
                    content_to_check = (title + snippet + link).lower()
                    if any(word in content_to_check for word in safety_blacklist):
                        continue
                        
                    formatted_items.append(RetrievalItem(
                        source="web",
                        title=title,
                        content=snippet,
                        link=link,
                        metadata={"query": query}
                    ))
                
                return formatted_items
            
            except asyncio.TimeoutError:
                logger.warning(f"[Researcher Tools] DDG Attempt {attempt + 1} timed out at async task level.")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error("[Researcher Tools] Web search exhausted retries due to strict timeout. Bypassing safely.")
                    return []
                    
            except Exception as e:
                logger.warning(f"[Researcher Tools] DDG Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                else:
                    # 超过两次(第3次失败)，打印错误日志（抛错级）但返回空列表，绝对不打断图的事件循环
                    logger.error(f"[Researcher Tools] Web search exhausted retries: {str(e)}")
                    return []

        return []

    @staticmethod
    async def search_weather_openmeteo(
        location: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[RetrievalItem]:
        """
        Asynchronously fetches localized weather forecasts invoking the Open-Meteo REST API.
        
        Args:
            location (str): Nominal destination for geocoding lookup.
            start_date (Optional[str]): Limit matching string.
            end_date (Optional[str]): Limit matching string.
            
        Returns:
            List[RetrievalItem]: Encapsulated weather analysis blocks.
        """
        def _fetch_weather() -> List[RetrievalItem]:
            logger.debug(f"[Researcher Tools] Fetching weather for: {location} (Date: {start_date} to {end_date})")
            
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=zh"
            try:
                with urllib.request.urlopen(geo_url, timeout=10) as response:
                    geo_data = json.loads(response.read().decode())
                
                if not geo_data.get("results"):
                    logger.warning(f"[Researcher Tools] Weather: Location not found for {location}")
                    return []
                
                res = geo_data["results"][0]
                lat, lon, name = res["latitude"], res["longitude"], res["name"]
                
                weather_base_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}&"
                    f"daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
                )
                
                weather_url = weather_base_url
                if start_date and end_date:
                    try:
                        datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.strptime(end_date, "%Y-%m-%d")
                    except ValueError:
                        pass
                
                with urllib.request.urlopen(weather_url, timeout=10) as response:
                    weather_data = json.loads(response.read().decode())
                
                daily = weather_data.get("daily", {})
                if not daily or not daily.get("time"):
                    return [RetrievalItem(
                        source="api_weather",
                        title=f"{name} 天气预报",
                        content="注：当前计划日期超出预报范围或无法获取准确数据。Open-Meteo 仅支持查询未来7-14天内的预报。",
                        link="https://open-meteo.com/",
                        metadata={"query": f"{location} 天气预报", "type": "weather"}
                    )]
                
                dates = daily.get("time", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                codes = daily.get("weathercode", [])
                
                code_map = {
                    0: "晴天", 1: "大部晴朗", 2: "多云", 3: "阴天",
                    45: "雾", 48: "结霜雾",
                    51: "毛毛雨: 轻微", 53: "毛毛雨: 中等", 55: "毛毛雨: 密集",
                    61: "下雨: 微弱", 63: "下雨: 中等", 65: "下雨: 强",
                    71: "降雪: 微弱", 73: "降雪: 中等", 75: "降雪: 强",
                    95: "雷雨"
                }
                
                lines: List[str] = []
                for i in range(len(dates)):
                    current_date_str = dates[i]
                    is_in_range = False
                    if start_date and end_date:
                        if start_date <= current_date_str <= end_date:
                            is_in_range = True

                    desc = code_map.get(codes[i], f"代码 {codes[i]}")
                    status_str = " [计划行程内]" if is_in_range else ""
                    lines.append(f"- {current_date_str}: {desc} ({min_temps[i]}°C ~ {max_temps[i]}°C){status_str}")
                
                if not lines:
                    return []

                content = "\n".join(lines)
                return [RetrievalItem(
                    source="api_weather",
                    title=f"{name} 未来7天预报 (含行程对比)",
                    content=content,
                    link="https://open-meteo.com/",
                    metadata={"query": f"{location} 天气预报", "type": "weather"}
                )]
                
            except Exception as e:
                logger.error(f"[Researcher Tools] Weather fetch failed: {str(e)}")
                return []

        return await asyncio.to_thread(_fetch_weather)

    @staticmethod
    def call_external_api(api_name: str, params: dict) -> str:
        """
        调用特定的旅游相关 API (如航司、马蜂窝等) (待实现)
        """
        # TODO: 实现特定的 API 调用逻辑
        return f"[Placeholder] API {api_name} results for params: {params}"

import asyncio
from typing import Optional, Dict, List
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from database.vector_db import search_similar_documents
from utils.logger import logger
from utils.prompt import research_query_prompt_template, research_filter_prompt_template
from agent.state import RetrievalItem
from agent.schema import ResearchPlan

class ResearcherTools:
    """
    Researcher 节点专用的工具集类，解耦具体的检索逻辑
    """
    
    @staticmethod
    async def generate_research_plan(state: Dict,LLM :ChatOpenAI) -> Optional[ResearchPlan]:
        """
        根据当前 TravelState 产生结构化的检索方案
        """
        user_profile = state.get("user_profile") or {}
        destination = user_profile.get("destination")
        if not destination:
            return None
        
        # 初始化模型与解析器
        llm = LLM
        parser = PydanticOutputParser(pydantic_object=ResearchPlan)
        
        # 获取最近K条对话（这里提取最近3条）
        messages = state.get("messages", [])
        # 取最后3条消息并转成文本，让研究员理解当下的语境
        recent_k_messages = messages[-3:] if len(messages) >= 3 else messages
        recent_context_str = "\n".join([f"{msg.type}: {msg.content}" for msg in recent_k_messages]) if recent_k_messages else "No recent context."
        
        # 变量准备
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
            response = await llm.ainvoke(prompt)
            plan = parser.parse(response.content) # type: ignore
            logger.debug(f"[Researcher Tools] Plan generated: {plan}")
            return plan
        except Exception as e:
            logger.error(f"[Researcher Tools] Plan generation failed: {str(e)}")
            dest_str = ",".join(destination) if isinstance(destination, list) else str(destination)
            # 降级方案：返回最基础的检索
            return ResearchPlan(
                local_query=dest_str,
                web_queries=[f"{dest_str} 旅游攻略"]
            )

    @staticmethod
    async def search_local_kt(query: str, k: int = 3) -> List[RetrievalItem]:
        """
        从本地向量知识库(ChromaDB)中检索信息，返回结构化列表
        """
        try:
            logger.debug(f"[Researcher Tools] Local RAG search for: {query}")
            search_results = await search_similar_documents(query, k)
            
            items = []
            for doc in search_results:
                items.append(RetrievalItem(
                    source="local",
                    link=None,
                    title="Knowledge Base Snippet",
                    content=doc.page_content,
                    metadata={"query": query}
                ))
            return items
        except Exception as e:
            logger.error(f"[Researcher Tools] Local search failed: {str(e)}")
            return []

    @staticmethod
    async def filter_retrieval_items(items: List[RetrievalItem], LLM: ChatOpenAI) -> List[RetrievalItem]:
        """
        [二级过滤] 将刚检索回来的列表经过轻量级的大模型质检，按生成时的 query 进行匹配，剔除内容毫不相关、营销号的杂音
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
                # 调用模型（为降低幻觉干扰，可自行调整温度）
                res = await LLM.ainvoke(prompt)
                answer_raw = res.content.strip()
                answer = answer_raw.upper()
                if "NO" in answer and "YES" not in answer:
                    logger.debug(f"[Researcher Tools] Filter dropped irrelevant item: {title}")
                    return None
                else:
                    return item
            except Exception:
                # 模型异常降级：宁可放过也不错杀
                return item

        # 并发质检
        tasks = [_check_single_item(item) for item in items]
        checked = await asyncio.gather(*tasks)
        return [raw for raw in checked if raw is not None]

    @staticmethod
    async def search_web_ddg(query: str, max_results: int = 10) -> List[RetrievalItem]:
        """
        使用 DuckDuckGo 进行在线搜索，获取最新的网页摘要。
        返回结构化的 RetrievalItem 列表。
        """
        
        # 针对网络波动设置重试次数和超时
        max_retries = 2
        timeout = 10  # 秒
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"[Researcher Tools] Web search (DDG) for: {query} (Attempt {attempt + 1})")
                
                from ddgs import DDGS
                
                def _sync_ddgs():
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", ResourceWarning)
                        with DDGS(timeout=timeout) as ddgs:
                            try:
                                # explicitly cast to list before leaving context
                                return list(ddgs.text(query, max_results=max_results, safesearch='on'))
                            finally:
                                pass
                            
                results = await asyncio.to_thread(_sync_ddgs)

                if not results:
                    return []
                
                # 定义敏感词黑名单逻辑，进一步增强安全性
                safety_blacklist = ["sex", "porn", "gamble", "赌博", "色情", "成人", "违禁"]
                
                formatted_items = []
                for res in results:
                    title = res.get("title", "No Title")
                    snippet = res.get("body", "No Content")
                    link = res.get("href", "#")
                    
                    # 检查标题和摘要是否包含敏感词
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
            
            except Exception as e:
                logger.warning(f"[Researcher Tools] DDG Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(1) # 短暂等待后重试
                    continue
                else:
                    logger.error(f"[Researcher Tools] Web search exhausted retries: {str(e)}")
                    return []

        return []

    @staticmethod
    async def search_weather_openmeteo(location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[RetrievalItem]:
        """
        使用 Open-Meteo 获取目的地的天气预报。
        支持指定日期范围。返回结构化的 RetrievalItem 列表。
        """
        import urllib.request
        import urllib.parse
        import json
        from datetime import datetime

        def _fetch_weather():
            logger.debug(f"[Researcher Tools] Fetching weather for: {location} (Date: {start_date} to {end_date})")
            # 1. Geocoding
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=zh"
            try:
                with urllib.request.urlopen(geo_url, timeout=10) as response:
                    geo_data = json.loads(response.read().decode())
                
                if not geo_data.get("results"):
                    logger.warning(f"[Researcher Tools] Weather: Location not found for {location}")
                    return []
                
                res = geo_data["results"][0]
                lat, lon, name = res["latitude"], res["longitude"], res["name"]
                
                # 2. Weather
                # 基本 URL
                weather_base_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
                
                # 如果有具体日期（且符合 API 格式 YYYY-MM-DD），尝试获取历史/预报混合数据
                # 注意：Open-Meteo 免费 API 的 forecast 接口通常支持未来 7-14 天
                # 如果日期在未来 14 天以后，该接口可能返回空。此处暂做基础日期过滤增强。
                weather_url = weather_base_url
                if start_date and end_date:
                    # 验证日期格式是否正确
                    try:
                        datetime.strptime(start_date, "%Y-%m-%d")
                        datetime.strptime(end_date, "%Y-%m-%d")
                        # 只有在日期范围内时，展示相关性更强。API 默认返回 7 天。
                        # 我们在客户端手动过滤日期。
                    except:
                        pass
                
                with urllib.request.urlopen(weather_url, timeout=10) as response:
                    weather_data = json.loads(response.read().decode())
                
                daily = weather_data.get("daily", {})
                if not daily:
                    return []
                
                dates = daily.get("time", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                codes = daily.get("weathercode", [])
                
                # 简单映射天气代码到中文描述
                code_map = {
                    0: "晴天", 1: "大部晴朗", 2: "多云", 3: "阴天",
                    45: "雾", 48: "结霜雾",
                    51: "毛毛雨: 轻微", 53: "毛毛雨: 中等", 55: "毛毛雨: 密集",
                    61: "下雨: 微弱", 63: "下雨: 中等", 65: "下雨: 强",
                    71: "降雪: 微弱", 73: "降雪: 中等", 75: "降雪: 强",
                    95: "雷雨"
                }
                
                lines = []
                for i in range(len(dates)):
                    # 日期过滤逻辑：如果设定了日期，只保留范围内的
                    current_date_str = dates[i]
                    if start_date and end_date:
                        if not (start_date <= current_date_str <= end_date):
                            continue

                    desc = code_map.get(codes[i], f"代码 {codes[i]}")
                    lines.append(f"- {current_date_str}: {desc} ({min_temps[i]}°C ~ {max_temps[i]}°C)")
                
                if not lines:
                    # 如果过滤后没数据，但也可能是因为日期太远。
                    # 给一个提示。
                    if start_date:
                        return [RetrievalItem(
                            source="api_weather",
                            title=f"{name} 天气信息",
                            content=f"抱歉，当前的免费 API 仅支持未来 7-14 天的精准预报。您计划的日期 {start_date} 暂无详细气象数据。",
                            link="https://open-meteo.com/",
                            metadata={"query": f"{location} 天气预报", "type": "weather"}
                        )]
                    return []

                content = "\n".join(lines)
                return [RetrievalItem(
                    source="api_weather",
                    title=f"{name} 旅行期间天气预报",
                    content=content,
                    link="https://open-meteo.com/",
                    metadata={"query": f"{location} 天气预报", "type": "weather"}
                )]
                
            except Exception as e:
                logger.error(f"[Researcher Tools] Weather fetch failed: {str(e)}")
                return []

        return await asyncio.to_thread(_fetch_weather)
                    desc = code_map.get(codes[i], f"未知代码 {codes[i]}")
                    lines.append(f"- 日期: {dates[i]} | 最高温: {max_temps[i]}°C | 最低温: {min_temps[i]}°C | 天气: {desc}")
                
                content = "\n".join(lines)
                
                return [RetrievalItem(
                    source="api_weather",
                    title=f"{name} 未来7天天气预报",
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

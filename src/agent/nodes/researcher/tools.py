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
                    reason_msg = answer_raw.replace("\n", " ")  # 将换行符替换为空格以便在日志里做单行展示
                    logger.debug(f"[Researcher Tools] Filter dropped irrelevant item: {title} | Reason: {reason_msg}")
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
    def call_external_api(api_name: str, params: dict) -> str:
        """
        调用特定的旅游相关 API (如天气、航司、马蜂窝等) (待实现)
        """
        # TODO: 实现特定的 API 调用逻辑
        return f"[Placeholder] API {api_name} results for params: {params}"

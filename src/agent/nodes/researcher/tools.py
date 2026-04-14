from typing import Optional, Dict, List
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
import time
from ddgs import DDGS


from database.vector_db import search_similar_documents
from utils.logger import logger
from utils.prompt import research_query_prompt_template
from agent.state import ResearchPlan, RetrievalItem

class ResearcherTools:
    """
    Researcher 节点专用的工具集类，解耦具体的检索逻辑
    """
    
    @staticmethod
    def generate_research_plan(state: Dict,LLM :ChatOpenAI) -> Optional[ResearchPlan]:
        """
        根据当前 TravelState 产生结构化的检索方案
        """
        core_req = state.get("core_requirements") or {}
        destination = core_req.get("destination")
        if not destination:
            return None
        
        # 初始化模型与解析器
        llm = LLM
        parser = PydanticOutputParser(pydantic_object=ResearchPlan)
        
        # 变量准备
        prompt = research_query_prompt_template.format(
            destination=destination,
            days=core_req.get("days"),
            people_count=core_req.get("people"),
            date=core_req.get("date"),
            tags=core_req.get("tags") or [],
            budget_limit=core_req.get("budget_limit") or 0,
            hard_constraints=core_req.get("hard_constraints", {}),
            soft_preferences=core_req.get("soft_preferences", {}),
            format_instructions=parser.get_format_instructions()
        )
        
        try:
            logger.debug(f"[Researcher Tools] Thinking about research plan for: {destination}")
            response = llm.invoke(prompt)
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
    def search_local_kt(query: str, k: int = 3) -> List[RetrievalItem]:
        """
        从本地向量知识库(ChromaDB)中检索信息，返回结构化列表
        """
        try:
            logger.debug(f"[Researcher Tools] Local RAG search for: {query}")
            search_results = search_similar_documents(query=query, k=k)
            
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
    def search_web_ddg(query: str, max_results: int = 10) -> List[RetrievalItem]:
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
                
                # DDGS 本身下初始化时支持 timeout
                with DDGS(timeout=timeout) as ddgs:
                    # 使用 safesearch='on' 开启安全搜索，过滤成人/违禁内容
                    results = list(ddgs.text(query, max_results=max_results, safesearch='on'))

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
                    time.sleep(1) # 短暂等待后重试
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

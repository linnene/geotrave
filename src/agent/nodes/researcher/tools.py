from typing import Optional, Dict, List
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from ddgs import DDGS

from database.vector_db import search_similar_documents
from utils.logger import logger
from utils.prompt import research_query_prompt_template
from agent.state import ResearchPlan

class ResearcherTools:
    """
    Researcher 节点专用的工具集类，解耦具体的检索逻辑
    """
    
    @staticmethod
    def generate_research_plan(state: Dict,LLM :ChatOpenAI) -> Optional[ResearchPlan]:
        """
        根据当前 TravelState 产生结构化的检索方案
        """
        destination = state.get("destination")
        if not destination:
            return None
        
        # 初始化模型与解析器
        llm = LLM
        parser = PydanticOutputParser(pydantic_object=ResearchPlan)
        
        # 变量准备
        prompt = research_query_prompt_template.format(
            destination=destination,
            tags=state.get("tags", []),
            hard_constraints=state.get("hard_constraints", {}),
            soft_preferences=state.get("soft_preferences", {}),
            format_instructions=parser.get_format_instructions()
        )
        
        try:
            logger.info(f"[Researcher Tools] Thinking about research plan for: {destination}")
            response = llm.invoke(prompt)
            plan = parser.parse(response.content)
            logger.info(f"[Researcher Tools] Plan generated: {plan}")
            return plan
        except Exception as e:
            logger.error(f"[Researcher Tools] Plan generation failed: {str(e)}")
            # 降级方案：返回最基础的检索
            return ResearchPlan(
                reasoning="LLM generation failed, falling back to basic query.",
                local_query=destination,
                web_queries=[f"{destination} 旅游攻略"]
            )

    @staticmethod
    def search_local_kt(query: str, k: int = 3) -> str:
        """
        从本地向量知识库(ChromaDB)中检索信息
        """
        try:
            logger.info(f"[Researcher Tools] Local RAG search for: {query}")
            search_results = search_similar_documents(query=query, k=k)
            if not search_results:
                return "No relevant information found in local KB."
            
            return "\n---\n".join([doc.page_content for doc in search_results])
        except Exception as e:
            logger.error(f"[Researcher Tools] Local search failed: {str(e)}")
            return f"Error during local search: {str(e)}"

    @staticmethod
    def search_web_ddg(query: str, max_results: int = 5) -> str:
        """
        使用 DuckDuckGo 进行在线搜索，获取最新的网页摘要。
        """
        try:
            logger.info(f"[Researcher Tools] Web search (DDG) for: {query}")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
            if not results:
                return f"No web results found for '{query}'."
            
            formatted_results = []
            for res in results:
                title = res.get("title", "No Title")
                snippet = res.get("body", "No Content")
                link = res.get("href", "#")
                formatted_results.append(f"Title: {title}\nContent: {snippet}\nLink: {link}")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            logger.error(f"[Researcher Tools] Web search failed: {str(e)}")
            return f"Error during web search: {str(e)}"

    @staticmethod
    def call_external_api(api_name: str, params: dict) -> str:
        """
        调用特定的旅游相关 API (如天气、航司、马蜂窝等) (待实现)
        """
        # TODO: 实现特定的 API 调用逻辑
        return f"[Placeholder] API {api_name} results for params: {params}"

from typing import List, Optional
from database.vector_db import search_similar_documents
from utils.logger import logger

class ResearcherTools:
    """
    Researcher 节点专用的工具集类，解耦具体的检索逻辑
    """
    
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
    def search_web_ddg(query: str) -> str:
        """
        使用 DuckDuckGo 进行在线搜索 (待详细实现)
        """
        # TODO: 集成 duckduckgo-search
        return f"[Placeholder] Web search results for: {query}"

    @staticmethod
    def call_external_api(api_name: str, params: dict) -> str:
        """
        调用特定的旅游相关 API (如天气、航司、马蜂窝等) (待实现)
        """
        # TODO: 实现特定的 API 调用逻辑
        return f"[Placeholder] API {api_name} results for params: {params}"

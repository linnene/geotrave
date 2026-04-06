from typing import Literal
from agent.nodes.researcher.tools import ResearcherTools
from agent.state import TravelState
from utils.logger import logger

def researcher_node(state: TravelState):
    """
    检索节点：解耦后的研究员节点，使用 ResearcherTools 进行多维度检索
    """
    destination = state.get("destination")
    if not destination:
        logger.info("[Researcher Node] No destination provided, retrieval skipped.")
        return {"retrieval_context": "No destination provided, retrieval skipped."}
    
    logger.info(f"[Researcher Node] Starting multi-source research for '{destination}'")
    
    # Local RAG
    local_info = ResearcherTools.search_local_kt(destination)
    
    # DuckDuckGo Web Search
    web_info = ResearcherTools.search_web_ddg(destination)
    

    final_context = f"### Local Knowledge Base:\n{local_info}\n\n### Web Search Result:\n{web_info}"
    
    return {"retrieval_context": final_context}

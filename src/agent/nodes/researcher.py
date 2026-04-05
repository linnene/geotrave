from typing import Literal
from database.vector_db import search_similar_documents
from agent.state import TravelState
from utils.logger import logger

def researcher_node(state: TravelState):
    """
    RAG 检索节点：根据目的地在向量数据库中检索背景资料
    """
    destination = state.get("destination")
    if not destination:
        logger.info("[Researcher Node] No destination provided, retrieval skipped.")
        return {"retrieval_context": "No destination provided, retrieval skipped."}
    
    logger.info(f"[Researcher Node] Querying knowledge base for '{destination}'")
    
    # Search
    search_results = []
    # search
    try:
        search_results = search_similar_documents(query=destination, k=3)
        logger.info(f"[Researcher Node] Querying knowledge About'{destination}':{search_results}")
    except Exception as e:
        logger.error(f"[Researcher Node] Network or Database error during retrieval: {str(e)}")

    if not search_results:
        context = "The relevant information could not be found in the knowledge base."
    else:
        # 将检索到的内容拼接
        context = "\n---\n".join([doc.page_content for doc in search_results])
    
    return {"retrieval_context": context}

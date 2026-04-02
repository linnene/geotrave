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
        logger.info("RESEARCHING: No destination provided, retrieval skipped.")
        return {"retrieval_context": "No destination provided, retrieval skipped."}
    
    logger.info(f"RESEARCHING: 开始从知识库中检索关于 '{destination}' 的资料...")
    
    # Search
    search_results = search_similar_documents(query=destination, k=3)
    
    if not search_results:
        context = "The relevant information could not be found in the knowledge base."
    else:
        # 将检索到的内容拼接
        context = "\n---\n".join([doc.page_content for doc in search_results])
    
    return {"retrieval_context": context}

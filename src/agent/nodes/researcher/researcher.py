#Researcher Node: Decoupled Researcher Node using ResearcherTools for multi-dimensional retrieval

from agent.nodes.researcher.tools import ResearcherTools
from agent.state import TravelState
from utils.logger import logger
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from utils.config import (
    RESEARCHER_MODEL_ID,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_API_KEY,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

# 使用配置中特定的 Researcher 模型
researcher_llm = ChatOpenAI(
    model=RESEARCHER_MODEL_ID,
    api_key=SecretStr(RESEARCHER_MODEL_API_KEY), 
    base_url=RESEARCHER_MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,                  
    disable_streaming=True,
)


def researcher_node(state: TravelState):
    """
    检索节点：解耦后的研究员节点，使用独立模型配置。
    """
    destination = state.get("destination")
    if not destination:
        logger.info("[Researcher Node] No destination provided, retrieval skipped.")
        return {"retrieval_context": "No destination provided, retrieval skipped."}
    
    logger.info(f"[Researcher Node] Starting research logic with model: {RESEARCHER_MODEL_ID}")
    
    # 1. 产生检索计划 (传递特定 LLM)
    plan = ResearcherTools.generate_research_plan(state, researcher_llm) # type: ignore
    # 映射到软偏好
    if not plan:
        # 如果计划生成失败，进行基础检索降级
        local_info = ResearcherTools.search_local_kt(destination)
        return {"retrieval_context": f"### Local Knowledge Base (Fallback):\n{local_info}"}
    
    
    # 2. 本地知识库检索
    local_info = ""
    if plan.local_query:
        local_info = ResearcherTools.search_local_kt(plan.local_query)
    
    # 3. 网络搜索 (多 Query)
    web_infos = []
    if plan.web_queries:
        for q in plan.web_queries:
            info = ResearcherTools.search_web_ddg(query=q, max_results=5)
            web_infos.append(f"Q: {q}\nA: {info}")
    
    # 4. 汇总
    final_context = f"### Local Knowledge Base:\n{local_info}\n\n"
    final_context += "### Web Search Results:\n" + ("\n---\n".join(web_infos) if web_infos else "No web results.")
    
    return {"retrieval_context": final_context}
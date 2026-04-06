#Researcher Node: Decoupled Researcher Node using ResearcherTools for multi-dimensional retrieval

from agent.nodes.researcher.tools import ResearcherTools
from agent.state import TravelState
from utils.logger import logger
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from utils.config import (
    OPENAI_API_KEY, 
    MODEL_BASE_URL, 
    MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

#Init Researcher Node's LLM (if needed for advanced retrieval or query reformulation in the future)
llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=SecretStr(OPENAI_API_KEY), 
    base_url=MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,                  
    disable_streaming=True,
)


def researcher_node(state: TravelState):
    """
    检索节点：解耦后的研究员节点，使用 ResearcherTools 多维度检索
    """
    destination = state.get("destination")
    if not destination:
        logger.info("[Researcher Node] No destination provided, retrieval skipped.")
        return {"retrieval_context": "No destination provided, retrieval skipped."}
    
    logger.info(f"[Researcher Node] Starting multi-source research logic for '{destination}'")
    
    # 1. 产生检索计划 (LLM 推理层)
    plan = ResearcherTools.generate_research_plan(state, llm)
    if not plan:
        # 如果计划生成失败，进行基础检索降级
        local_info = ResearcherTools.search_local_kt(destination)
        return {"retrieval_context": f"### Local Knowledge Base (Fallback):\n{local_info}"}
    
    logger.info(f"[Researcher Node] Plan: {plan.reasoning}")
    
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
    final_context = f"### Researcher Analysis:\n{plan.reasoning}\n\n"
    final_context += f"### Local Knowledge Base:\n{local_info}\n\n"
    final_context += "### Web Search Results:\n" + ("\n---\n".join(web_infos) if web_infos else "No web results.")
    
    return {"retrieval_context": final_context}
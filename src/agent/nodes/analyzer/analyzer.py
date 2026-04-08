# Analyzer Node: Extracting Travel Information from User Conversations

import datetime
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langchain_core.output_parsers import PydanticOutputParser


from agent.state import TravelState, TravelInfo
from utils.prompt import analyzer_prompt_template
from utils.logger import logger

from utils.config import (
    ANALYZER_MODEL_API_KEY, 
    ANALYZER_MODEL_BASE_URL, 
    ANALYZER_MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

# Init Analyzer's LLM with dedicated config
llm = ChatOpenAI(
    model=ANALYZER_MODEL_ID,
    api_key=SecretStr(ANALYZER_MODEL_API_KEY), 
    base_url=ANALYZER_MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,                  
    disable_streaming=True,
)

async def analyzer_node(state: TravelState):
    """
    分析师节点：从聊天历史中提取结构化的旅行需求。
    """
    logger.debug("[Analyzer Node] Start processing message history...")
    
    # 获取对话历史并设置当前日期
    messages = state["messages"]
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    logger.debug(f"[Analyzer Node] Extracting info for date: {current_date}")
    
    try:
        parser = PydanticOutputParser(pydantic_object=TravelInfo)
        
        # 准备提示词并注入
        prompt_value = analyzer_prompt_template.format(
            current_date=current_date,
            history=messages,
            format_instructions=parser.get_format_instructions()
        )
        
        # 调用 LLM 进行分析
        logger.debug("[Analyzer Node] Invoking LLM for demand modeling...")
        chain = llm | parser
        result = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Analyzer Node] Analysis complete: {result.destination} for {result.days} days.")
        if result.tags:
            logger.debug(f"[Analyzer Node] Identified Tags: {result.tags}")
        
        # 回写至全局状态 (注意字段名需与 TravelState 定义严格对齐)
        return {
            "messages": [AIMessage(content=result.reply)],
            "destination": result.destination,
            "days": result.days,
            "date": result.date,
            "people": result.people_count, # 映射到 state 中的 people
            "budget_limit": result.budget_limit, # 映射到 state 中的 budget_limit
            "hard_constraints": result.hard_constraints,
            "soft_preferences": result.soft_preferences,
            "tags": result.tags,
        }
    except Exception as e:
        logger.error(f"[Analyzer Node] Failed to extract user info: {str(e)}")
        # 错误时保证最基本的回复，不中断工作流
        return {
            "messages": [AIMessage(content="抱歉，在理解您的需求时遇到了一点小麻烦，能请您再详细说明一下吗？")]
        }
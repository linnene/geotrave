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
    OPENAI_API_KEY, 
    MODEL_BASE_URL, 
    MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

# Init Analyzer's LLM
llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=SecretStr(OPENAI_API_KEY), 
    base_url=MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,                  
    disable_streaming=True,
)

async def analyzer_node(state: TravelState):
    """
    分析师节点：从聊天历史中提取结构化的旅行需求。
    """
    logger.info("[Analyzer Node] Start processing message history...")
    
    # 获取对话历史并设置当前日期
    messages = state["messages"]
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"[Analyzer Node] Extracting info for date: {current_date}")
    
    try:
        parser = PydanticOutputParser(pydantic_object=TravelInfo)
        
        # 准备提示词并注入
        prompt_value = analyzer_prompt_template.format(
            current_date=current_date,
            history=messages,
            format_instructions=parser.get_format_instructions()
        )
        
        # 调用 LLM 进行分析
        logger.info("[Analyzer Node] Invoking LLM for demand modeling...")
        chain = llm | parser
        result = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Analyzer Node] Analysis complete. Destination: {result.destination}, Days: {result.days}")
        if result.tags:
            logger.info(f"[Analyzer Node] Identified Tags: {result.tags}")
        
        # 回写至全局状态
        return {
            "messages": [AIMessage(content=result.reply)],
            "destination": result.destination,
            "days": result.days,
            "date": result.date,
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
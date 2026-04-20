"""
Module: src.agent.nodes.analyzer.analyzer
Responsibility: Extracts structured travel requirements (destination, dates, budget, etc.) from conversation history.
Parent Module: src.agent.nodes.analyzer
Dependencies: datetime, json, langchain_core, src.agent.state, src.agent.schema, src.utils

Refactoring Standard: Centralized LLM factory usage, robust type safety, and standardized logging.
"""

import datetime
import json
from typing import Dict, Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser

from src.agent.state import TravelState
from src.agent.schema import TravelInfo
from src.utils import logger, analyzer_prompt_template, LLMFactory

# 1. Init Analyzer's LLM via Factory
llm = LLMFactory.get_model("analyzer")

async def analyzer_node(state: TravelState) -> Dict[str, Any]:
    """
    Extracts structured travel information from chat history.
    
    Args:
        state (TravelState): Current graph state.
        
    Returns:
        Dict[str, Any]: State updates including AI reply, research flag, and profile.
    """
    logger.debug("[Analyzer Node] Start processing message history...")
    
    messages = state.get("messages", [])
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        parser = PydanticOutputParser(pydantic_object=TravelInfo)
        current_profile = state.get("user_profile") or {}
        
        prompt_value = analyzer_prompt_template.format(
            current_date=current_date,
            history=messages,
            current_profile=json.dumps(current_profile, ensure_ascii=False, indent=2),
            format_instructions=parser.get_format_instructions()
        )
        
        logger.debug("[Analyzer Node] Invoking LLM for demand modeling...")
        chain = llm | parser
        result: TravelInfo = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Analyzer Node] Analysis complete for: {result.user_profile.destination}")
        
        return {
            "messages": [AIMessage(content=result.reply)],
            "needs_research": result.needs_research,
            "user_profile": result.user_profile.model_dump()
        }
    except Exception as e:
        logger.error(f"[Analyzer Node] Failed to extract user info: {str(e)}")
        return {
            "messages": [AIMessage(content="抱歉，在理解您的需求时遇到了一点小麻烦，能请您再详细说明一下吗？")],
            "needs_research": False
        }
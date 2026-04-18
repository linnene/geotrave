"""
Analyzer Node: Extracting Travel Information from User Conversations.

This node analyzes message history to extract structured travel preferences.

Parent Module: src.agent.nodes
Dependencies: agent.factory, agent.schema, agent.state, utils.prompt, utils.logger
"""

import datetime
import json
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser

from agent.state import TravelState
from agent.schema import TravelInfo
from agent.factory import LLMFactory
from utils.prompt import analyzer_prompt_template
from utils.logger import logger

# Init Analyzer LLM using the centralized factory
llm = LLMFactory.create_analyzer_llm()

async def analyzer_node(state: TravelState):
    """
    Extract structured travel requirements from message history.
    
    Analyzes historical dialogue and updates the user profile incrementally.
    """
    logger.debug("[Analyzer Node] Starting demand extraction...")
    
    messages = state.get("messages", [])
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    current_profile = state.get("user_profile") or {}
    
    try:
        parser = PydanticOutputParser(pydantic_object=TravelInfo)
        
        # Prepare prompt with history and current profile baseline
        prompt_value = analyzer_prompt_template.format(
            current_date=current_date,
            history=messages,
            current_profile=json.dumps(current_profile, ensure_ascii=False, indent=2),
            format_instructions=parser.get_format_instructions()
        )
        
        # Execute analysis chain
        chain = llm | parser
        result = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Analyzer Node] Success: {result.user_profile.destination} ({result.user_profile.days} days).")
        
        # Logic: needs_research should only trigger if internal info is COMPLETE enough for a plan 
        # OR if explicit research (like hotels/flights) is needed. 
        # Note: weather and external API logic is handled by Researcher later.
        
        # Return updated state dictionary
        return {
            "messages": [AIMessage(content=result.reply)],
            "needs_research": result.needs_research,
            "user_profile": result.user_profile.model_dump()
        }
        
    except Exception as e:
        logger.error(f"[Analyzer Node] Extraction failed: {str(e)}")
        # Graceful fallback to avoid breaking the graph workflow
        return {
            "messages": [AIMessage(content="I had a little trouble understanding your request. Could you please provide more details?")],
            "needs_research": False
        }
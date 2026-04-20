"""
Module: src.agent.nodes.router.router
Responsibility: Gateway node for intent classification, security screening (malicious prompt detection), and conversation flow routing.
Parent Module: src.agent.nodes.router
Dependencies: langchain_core, src.utils, src.agent.state

Refactoring Standard: Fully asynchronous, localized error handling, and separation of concern.
"""

from typing import Dict, Any

from langchain_core.messages import AIMessage

from src.agent.state import TravelState
from src.agent.schema import RouterIntent
from src.utils import logger, router_prompt_template, LLMFactory

# 1. Init Router LLM via Factory
llm = LLMFactory.get_model("router")


async def router_node(state: TravelState) -> Dict[str, Any]:
    """
    Responsible for front-end truncation, intent classification and defense against malicious prompt injection.
    
    Args:
        state (TravelState): Current graph state.
        
    Returns:
        Dict[str, Any]: State updates with latest_intent.
    """
    logger.debug("[Router Gateway Node] Inspecting incoming input for intent...")
    messages = state.get("messages", [])
    
    if not messages:
        logger.warning("[Router Gateway Node] No messages to parse.")
        return {"messages": []}

    latest_user_msg = messages[-1].content if messages else ""

    try:
        from langchain_core.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=RouterIntent)
        
        prompt_value = router_prompt_template.format(
            history=messages[:-1] if len(messages) > 1 else "",
            user_input=latest_user_msg,
            format_instructions=parser.get_format_instructions()
        )

        # Standard chain execution
        chain = llm | parser
        parsed: RouterIntent = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Router Gateway Node] Parsed intent: {parsed.enum_intent}, Safe: {parsed.is_safe}")
        
        if not parsed.is_safe or parsed.enum_intent == "chit_chat_or_malicious":
            msg_content = parsed.reply_for_malicious or "请咱们把话题拉回旅行规划上好吗？"
            return {
                "messages": [AIMessage(content=msg_content)],
                "latest_intent": "chit_chat_or_malicious",
                "needs_research": False
            }
        
        return {
             "latest_intent": parsed.enum_intent,
             "needs_research": state.get("needs_research", False)
        }

    except Exception as e:
        logger.error(f"[Router Gateway Node] Error parsing request: {e}")
        return {
            "latest_intent": "new_destination",
            "needs_research": state.get("needs_research", False)
        }
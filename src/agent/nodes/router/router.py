"""
Router Node: Intent classification and safety filtering.

This node determines the next step in the graph based on user intent 
and filters out malicious or irrelevant inputs.

Parent Module: src.agent.nodes
Dependencies: agent.factory, agent.state, utils.prompt
"""

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from agent.state import TravelState
from agent.factory import LLMFactory
from utils.prompt import router_prompt_template
from utils.logger import logger

# Init Router LLM using the factory
llm = LLMFactory.create_router_llm()

# 2. Define Output Schema
class RouterIntent(BaseModel):
    """Schema for classification of user intent by the Router node."""
    enum_intent: str = Field(
        ...,
        description="Intent types: `new_destination`, `update_preferences`, `chit_chat_or_malicious`, `confirm_and_plan`, `re_recommend`"
    )
    is_safe: bool = Field(..., description="Whether the input is safe (True) or malicious/irrelevant (False).")
    reply_for_malicious: str = Field(
        default="",
        description="A default refusal reply if the input is deemed unsafe."
    )


async def router_node(state: TravelState):
    """
    Determine user intent and perform safety filtering.
    
    This node intercepts malicious inputs or classifies valid requests to route
    the conversation through the appropriate graph branches.
    """
    logger.debug("[Router Node] Inspecting user input for intent...")
    messages = state.get("messages", [])
    
    if not messages:
        logger.warning("[Router Node] No messages to analyze.")
        return {"messages": []}

    latest_user_msg = messages[-1].content if messages else ""

    try:
        parser = PydanticOutputParser(pydantic_object=RouterIntent)
        
        prompt_value = router_prompt_template.format(
            history=messages[:-1] if len(messages) > 1 else "",
            user_input=latest_user_msg,
            format_instructions=parser.get_format_instructions()
        )

        chain = llm | parser
        parsed: RouterIntent = await chain.ainvoke(prompt_value)
        
        logger.info(f"[Router Node] Parsed intent: {parsed.enum_intent}, Safe: {parsed.is_safe}")
        
        # Intercept unsafe or irrelevant inputs
        if not parsed.is_safe or parsed.enum_intent == "chit_chat_or_malicious":
            msg_content = parsed.reply_for_malicious or "Let's focus on your travel planning!"
            return {
                "messages": [AIMessage(content=msg_content)],
                "latest_intent": "chit_chat_or_malicious",
                "needs_research": False
            }
        
        # Pass the identified intent for conditional routing
        return {
             "latest_intent": parsed.enum_intent,
             "needs_research": state.get("needs_research", False)
        }

    except Exception as e:
        logger.error(f"[Router Node] Intent classification failed: {e}")
        # Default fallback to preserve system operation
        return {
            "latest_intent": "new_destination",
            "needs_research": state.get("needs_research", False)
        }

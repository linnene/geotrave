"""
Module: src.agent.rules
Responsibility: Implements conditional edge logic for LangGraph routing.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.utils

Refactoring Standard: Strict absolute imports, enhanced logging, and explicit routing logic.
"""

from langgraph.graph import END
from src.agent.state import TravelState
from src.utils import logger

def route_after_router(state: TravelState) -> str:
    """
    Decides the next node after the Router gateway based on the classified intent.
    
    Args:
        state (TravelState): Current graph state.
        
    Returns:
        str: Candidate node name or END.
    """
    intent = state.get("latest_intent")
    logger.debug(f"[Router Rule] Inspecting intent: {intent}")
    
    if intent == "chit_chat_or_malicious":
        logger.info("[Router Rule] Input rejected or chit-chat. Halt and return to user.")
        return END

    elif intent in ["new_destination", "update_preferences"]:
        logger.info("[Router Rule] Core preference update detected. Routing to Analyzer.")
        return "analyzer"

    elif intent in ["re_recommend", "confirm_and_plan"]:
        # Logic matches exactly the original behavior: forward to researcher for these intents
        logger.info(f"[Router Rule] Action intent: {intent}. Forwarding to Researcher.")
        return "researcher"

    else:
        logger.warning(f"[Router Rule] Fallback for intent '{intent}'. Routing to Analyzer.")
        return "analyzer"

def route_after_analyzer(state: TravelState) -> str:
    """
    Decides whether to proceed to retrieval (researcher) based on analyzer results.
    
    Args:
        state (TravelState): Current graph state.
        
    Returns:
        str: Candidate node name or END.
    """
    core_req = state.get("user_profile") or {}
    destination = core_req.get("destination")
    days = core_req.get("days")
    people = core_req.get("people_count")          
    date = core_req.get("date")
    needs_research = state.get("needs_research", False)
    
    # 1. Base information check (Logical Requirement for Planning)
    if not (destination and days and people and date):
        logger.debug("[Router Rule] Base information incomplete. Waiting for user response.")
        return END

    # 2. Decision based on Analyzer's explicit research flag
    if needs_research:
        logger.info(f"[Router Rule] Analyzer requested research. Routing to 'researcher' for: {destination}")
        return "researcher"

    logger.info("[Router Rule] Base info complete, but no research required. Ending turn.")
    return END

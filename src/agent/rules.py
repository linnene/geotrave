from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

def route_after_router(state: TravelState):
    """
    Handles flow distribution after initial intent classification.
    """
    intent = state.get("latest_intent")
    logger.debug(f"[Router Rule] Inspecting intent: {intent}")
    
    if intent == "chit_chat_or_malicious":
        logger.info("[Router Rule] Input rejected. Halt and return to user.")
        return END

    elif intent in ["new_destination", "update_preferences"]:
        logger.info("[Router Rule] Core preference updated. Routing to Analyzer.")
        return "analyzer"

    elif intent in ["re_recommend", "confirm_and_plan"]:
        logger.info(f"[Router Rule] Action intent: {intent}. Forwarding to Researcher.")
        return "researcher"

    else:
        logger.warning(f"[Router Rule] Fallback for unknown intent '{intent}'. Routing to Analyzer.")
        return "analyzer"

def route_after_analyzer(state: TravelState):
    """
    Routing logic based on extracted user profile and research needs.
    """
    core_req = state.get("user_profile") or {}
    destination = core_req.get("destination", [])
    
    # Force boolean value for state field
    needs_research = state.get("needs_research")
    if needs_research is None:
        needs_research = False
    
    logger.debug(f"[Router Rule] Decision checking: Dest={destination}, NeedsResearch={needs_research}")
    
    # Base condition: Must have a destination to proceed with research
    if not destination or len(destination) == 0:
        logger.debug(f"[Router Rule] Destination missing or empty. Waiting for user response.")
        return END

    # Trigger research if requested by Analyzer
    if needs_research:
        logger.info(f"[Router Rule] Analyzer explicitly requested research. Routing to 'researcher'.")
        return "researcher"

    logger.info(f"[Router Rule] Information sufficient but no research needed. Ending turn.")
    return END
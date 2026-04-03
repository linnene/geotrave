from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

# 根据 Anaslyzer result 选择下一步
def route_after_analyzer(state: TravelState):
    
    destination = state.get("destination")
    
    # Print routing decisions for debugging
    if destination:
        logger.info(f"[Router] Destination found: '{destination}', routing to 'researcher'.")
        return "researcher"
    
    logger.info("[Router] No destination found, ending graph.")
    return END

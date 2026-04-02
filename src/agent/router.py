from langgraph.graph import END
from agent.state import TravelState

def route_after_analyzer(state: TravelState):
    """
    Judgment logic: If the destination is not determined, end (ask the user);
    If the destination has been determined, enter data collection (researcher)。
    """
    destination = state.get("destination")
    
    # Print routing decisions for debugging
    if destination:
        return "researcher"
    
    return END

from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

def route_after_analyzer(state: TravelState):
    """
    Judgment logic: If the destination is not determined, end (ask the user);
    If the destination has been determined, enter data collection (researcher)。
    """
    destination = state.get("destination")
    
    # Print routing decisions for debugging
    if destination:
        logger.info(f"ROUTING: 提取到目的地 '{destination}'，即将进入 RESEARCHER 节点。")
        return "researcher"
    
    logger.info("ROUTING: 未获取到明确的目的地，暂停当前图谱，等待用户补充。")
    return END

from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

# 根据 Analyzer result 选择下一步
# TODO: 添加更丰富的逻辑，是否转向检索节点
def route_after_analyzer(state: TravelState):
    
    destination = state.get("destination")
    days = state.get("days")
    budget = state.get("budget")
    
    # 必须要包含核心要素才允许流转到下一级
    if destination and days and budget:
        logger.info(f"[Router] All requirements extracted (Dest: {destination}, Days: {days}, Budget: {budget}), routing to 'researcher'.")
        return "researcher"
    
    logger.info("[Router] Requirements incomplete, waiting for user response.")
    return END

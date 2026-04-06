from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

def route_after_analyzer(state: TravelState):
    """
    路由逻辑：基于 Analyzer 提取的状态决定流程。
    
    1. 必须要包含核心要素 (目的地、天数) 才允许流转到 Researcher 节点。
    2. 如果核心信息不全，则留在 END (由 API 层根据 Analyzer 的 reply 返回追问)。
    """
    destination = state.get("destination")
    days = state.get("days")
    
    # 目的地和天数是启动 RAG 和规划的最小必要集
    # 预算设定为软约束或有默认值的情况，不作为强制阻断
    if destination and days:
        logger.info(f"[Router] Core requirements detected (Dest: {destination}, Days: {days}), routing to 'researcher'.")
        return "researcher"
    
    logger.info("[Router] Key information (destination/days) missing, waiting for user further input.")
    return END

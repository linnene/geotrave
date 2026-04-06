from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

def route_after_analyzer(state: TravelState):
    """
    路由逻辑：基于 Analyzer 提取的状态决定流程。
    
    1. 必须要包含核心基础信息 (目的地、天数、人数、日期) 才允许流转到 Researcher 节点。
    2. 如果基础信息不全，则留在 END (由 API 层根据 Analyzer 的 reply 返回追问)。
    """
    # 从 state 中读取字段，注意应与 state.py 中定义的 TravelState 键名保持一致
    destination = state.get("destination")
    days = state.get("days")
    people = state.get("people")          # TravelState 中定义为 'people'
    date = state.get("date")
    budget = state.get("budget_limit")    # TravelState 中定义为 'budget_limit'
    
    logger.info(f"[Router] Decision checking: Dest={destination}, Days={days}, Date={date}, People={people}, Budget={budget}")
    
    # 基础信息闭环判断：目的地、天数、人数、日期
    if destination and days and people and date:
        logger.info(f"[Router] Base requirements satisfied. Routing to 'researcher'.")
        return "researcher"
    
    logger.info(f"[Router] Base information incomplete. Waiting for user response.")
    return END

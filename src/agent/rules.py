from langgraph.graph import END
from agent.state import TravelState
from utils.logger import logger

def route_after_router(state: TravelState):
    """
    负责在前置网关判断用户的原始意图后进行分流。
    考虑到 Recommender（推荐节点）和 Planner（计划节点）尚未开发，目前仅复用已拥有的 analyzer 和 researcher
    """
    intent = state.get("latest_intent")
    logger.debug(f"[Router Rule] Inspecting intent: {intent}")
    
    if intent == "chit_chat_or_malicious":
        # 被判定为闲聊或恶意注入，不再流转，直接结束（Router 节点已预先抛出了拒答回复）
        logger.info("[Router Rule] Input rejected. Halt and return to user.")
        return END

    elif intent in ["new_destination", "update_preferences"]:
        # 新目的地或更改偏好，这些都会影响基础白板特征，必须先经过分析师提炼
        logger.info("[Router Rule] Core preference updated. Routing to Analyzer.")
        return "analyzer"

    elif intent in ["re_recommend", "confirm_and_plan"]:
        # "再推荐一份" 或者 "确认去排线"：由于本版本还没写 Recommender 和 Planner
        # 就权当是核心信息充沛的下发，重新交由 researcher 再搜一次或流向最后实现的子图边界。
        logger.info(f"[Router Rule] Action intent: {intent}. Forwarding to connected downstream (Researcher).")
        return "researcher"

    else:
        # 异常或不在枚举范围内，保守回到分析师重新提取
        logger.warning(f"[Router Rule] Fallback for unknown intent '{intent}'. Routing to Analyzer.")
        return "analyzer"

def route_after_analyzer(state: TravelState):
    """
    路由逻辑：基于 Analyzer 提取的状态决定流程。
    
    1. 必须要包含核心基础信息 (目的地、天数、人数、日期) 才允许流转到 Researcher 节点。
    2. 如果基础信息不全，则留在 END (由 API 层根据 Analyzer 的 reply 返回追问)。
    """
    # 从 state 中读取字段，注意应与 state.py 中定义的 TravelState 键名保持一致
    core_req = state.get("core_requirements") or {}
    destination = core_req.get("destination")
    days = core_req.get("days")
    people = core_req.get("people")          # CoreRequirementState 中定义为 'people'
    date = core_req.get("date")
    budget = core_req.get("budget_limit")    # CoreRequirementState 中定义为 'budget_limit'
    
    logger.debug(f"[Router] Decision checking: Dest={destination}, Days={days}, Date={date}, People={people}, Budget={budget}")
    
    # 基础信息闭环判断：目的地、天数、人数、日期
    if destination and days and people and date:
        logger.info(f"[Router] Routing to 'researcher' for: {destination}")
        return "researcher"
    
    logger.debug(f"[Router] Base information incomplete. Waiting for user response.")
    return END

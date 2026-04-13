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
    
    1. 必须要包含核心基础信息 (目的地、天数、人数、日期) 才允许进行后续节点。
    2. 如果基础信息不全，则留在 END 等待用户补充。
    3. 取消被动的状态快照对比，而是听从分析师大模型的自主决断(needs_research)，决定是否主动进入 researcher 节点。
    """
    core_req = state.get("core_requirements") or {}
    destination = core_req.get("destination")
    days = core_req.get("days")
    people = core_req.get("people")          
    date = core_req.get("date")
    budget = core_req.get("budget_limit")    
    needs_research = state.get("needs_research", False)
    
    logger.debug(f"[Router Rule] Decision checking: Dest={destination}, Days={days}, Date={date}, People={people}, Budget={budget}, NeedsResearch={needs_research}")
    
    # 1. 基础信息不全
    if not (destination and days and people and date):
        logger.debug(f"[Router Rule] Base information incomplete. Waiting for user response.")
        return END

    # 2. 分析师判断需要重搜（例如：刚收集完/核心要素发生变更）
    if needs_research:
        logger.info(f"[Router Rule] Analyzer explicitly requested research. Routing to 'researcher' for: {destination}")
        return "researcher"

    # 3. 基础信息全，且无需搜索（可能是闲聊，或者一些不需要重新搜的微小改动）
    logger.info(f"[Router Rule] Base info complete, but Analyzer decided no research needed. Ending turn.")
    return END

"""
Module: src.agent.nodes.reply.node
Responsibility: Generates natural language responses in 3 scenarios:
  - BLOCK   (gateway routed): polite security redirect
  - GUIDE   (manager routed, core incomplete): follow-up questions
  - RECOMMEND (recommender routed): present recommendations
Parent Module: src.agent.nodes
Dependencies: langchain_core, src.agent.state, src.utils
"""

import time
from typing import Any, Dict, Literal

from langchain_core.messages import AIMessage, HumanMessage
from src.agent.state import TravelState
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, get_beijing_time_now
from .config import TEMPERATURE, MAX_TOKENS

logger = get_logger("ReplyNode")

Scenario = Literal["block", "recommend", "guide"]

DIM_LABELS = {"destination": "目的地", "accommodation": "住宿", "dining": "餐饮"}
_DIM_ORDER = ("destination", "accommodation", "dining")


def _detect_scenario(state: TravelState) -> Scenario:
    """基于 state 信号判断 Reply 当前应承担的角色。"""
    needs_exit = state.get("needs_exit", False)
    signs = state.get("execution_signs")
    is_safe = signs.is_safe if signs else True
    rec_data = state.get("recommendation_data")

    if needs_exit and not is_safe:
        return "block"
    if rec_data:
        return "recommend"
    return "guide"


def _get_block_context(state: TravelState) -> Dict[str, str]:
    """从 state 中提取安全拦截所需的上下文。"""
    trace_history = state.get("trace_history", [])
    category = "违反安全策略"
    for t in reversed(trace_history):
        if t.node == "gateway" and t.status == "BLOCKED":
            detail = t.detail or {}
            category = detail.get("category", category)
            break

    messages = state.get("messages", [])
    block_reply_text = ""
    if messages:
        last_msg = messages[-1]
        block_reply_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    return {"block_category": category, "block_reply_text": block_reply_text}


def _get_recommend_context(state: TravelState) -> Dict[str, str]:
    """从 state 中提取推荐呈现所需的上下文。"""
    rec_data = state.get("recommendation_data") or {}
    signs = state.get("execution_signs")
    recommended_dims = list(getattr(signs, "recommended_dimensions", []) or []) if signs else []

    current_dim = recommended_dims[-1] if recommended_dims else None
    if not current_dim:
        for dim in _DIM_ORDER:
            if dim in rec_data:
                current_dim = dim
                break

    dim_data = rec_data.get(current_dim, {}) if current_dim else {}
    items = dim_data.get("items", [])
    strategy = dim_data.get("strategy", "")
    tip = dim_data.get("tip", "")

    item_lines = []
    for idx, item in enumerate(items, 1):
        name = item.get("name", "")
        features = item.get("features", "")
        reason = item.get("reason", "")
        rating = item.get("rating", 0)
        stars = "★" * int(rating) + ("☆" if rating - int(rating) >= 0.5 else "")
        item_lines.append(
            f"  [{idx}] {name} | 评分: {stars} {rating}/5\n"
            f"      亮点: {features}\n"
            f"      推荐理由: {reason}"
        )
    items_text = "\n".join(item_lines) if item_lines else "（暂无推荐项）"

    remaining = [d for d in _DIM_ORDER if d not in recommended_dims]
    remaining_labels = [DIM_LABELS.get(d, d) for d in remaining]

    profile = state.get("user_profile")
    profile_text = profile.model_dump_json(indent=2, ensure_ascii=False) if profile else "暂无画像"

    return {
        "user_request": state.get("user_request", "旅行规划"),
        "user_profile": profile_text,
        "focus_dimension": DIM_LABELS.get(current_dim, current_dim or "推荐"),
        "strategy": strategy,
        "recommendation_items": items_text,
        "tip": tip,
        "remaining_dimensions": "、".join(remaining_labels) if remaining_labels else "无（全部维度已完成）",
    }


async def reply_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()

    scenario = _detect_scenario(state)
    logger.info(f"Reply — scenario={scenario}")

    # --- Block 分支 ---
    if scenario == "block":
        ctx = _get_block_context(state)
        prompt_str = prompt.reply_block.format(
            current_time=get_beijing_time_now(),
            block_category=ctx["block_category"],
            block_reply_text=ctx["block_reply_text"],
        )
        trace = build_trace(
            "reply",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"scenario": "block", "category": ctx["block_category"]},
        )

    # --- Recommend 分支 ---
    elif scenario == "recommend":
        ctx = _get_recommend_context(state)
        prompt_str = prompt.reply_recommend.format(
            current_time=get_beijing_time_now(),
            user_request=ctx["user_request"],
            user_profile=ctx["user_profile"],
            focus_dimension=ctx["focus_dimension"],
            strategy=ctx["strategy"],
            recommendation_items=ctx["recommendation_items"],
            tip=ctx["tip"],
            remaining_dimensions=ctx["remaining_dimensions"],
        )
        trace = build_trace(
            "reply",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"scenario": "recommend", "dimension": ctx["focus_dimension"]},
        )

    # --- Guide 分支 (existing logic) ---
    else:
        missing_fields = state.get("missing_fields", [])
        current_profile = state.get("user_profile")
        user_request = state.get("user_request", "")
        messages = state.get("messages", [])

        last_user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage) or (hasattr(m, "type") and m.type == "human"):
                last_user_msg = m.content
                break

        profile_json = current_profile.model_dump_json(indent=2, ensure_ascii=False) if current_profile else "{}"
        prompt_str = prompt.reply.format(
            current_time=get_beijing_time_now(),
            last_user_message=last_user_msg,
            user_request=user_request,
            current_profile=profile_json,
            missing_fields=", ".join(missing_fields) if missing_fields else "全量信息已具备，正在深化细节",
        )
        trace = build_trace(
            "reply",
            "SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"scenario": "guide", "missing_fields": missing_fields},
        )

    # --- LLM invoke ---
    llm = LLMFactory.get_model("Reply", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

    try:
        response = await llm.ainvoke(prompt_str)
        reply_text = response.content if hasattr(response, "content") else str(response)
        if isinstance(reply_text, list):
            reply_text = "".join(
                [i.get("text", "") if isinstance(i, dict) else str(i) for i in reply_text]
            )
    except Exception as exc:
        logger.error(f"Reply generation failed: {str(exc)}", exc_info=True)
        if scenario == "block":
            reply_text = "系统检测到异常输入，请提出与旅行规划相关的问题。"
        elif scenario == "recommend":
            reply_text = "为您准备了推荐方案，但系统暂时无法完整呈现。请稍后重试或换个方向继续提问。"
        else:
            reply_text = "我还需要了解更多关于您旅行意图的信息，比如目的地或天数。您可以详细说说吗？"

    logger.debug(f"Generated reply ({scenario}): {reply_text[:80]}...")

    return {
        "messages": [AIMessage(content=reply_text)],
        "trace_history": [trace],
    }

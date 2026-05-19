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
from src.utils.config import DIM_LABELS
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import prompt
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace, get_beijing_time_now
from .config import TEMPERATURE, MAX_TOKENS

logger = get_logger("ReplyNode")

Scenario = Literal["block", "recommend", "guide"]


def _label_dim(dim: str) -> str:
    """返回维度的中文标签，未知维度返回原始名称。"""
    return DIM_LABELS.get(dim, dim)


def _detect_scenario(state: TravelState) -> Scenario:
    """基于 state 信号判断 Reply 当前应承担的角色。"""
    needs_exit = state.get("needs_exit", False)
    signs = state.get("execution_signs")
    is_safe = signs.is_safe if signs else True
    rec_data = state.get("recommendation_data")
    route_meta = state.get("route_metadata")
    # 仅当 Manager 本轮明确路由到 recommender 且推荐数据存在时，才进入推荐呈现模式。
    # 避免 Manager 路由到 reply（guide）时因旧数据而误入推荐模式，
    # 也避免 Recommender 失败后 Reply 呈现不相关维度的旧数据。
    routed_to_recommender = getattr(route_meta, 'next_node', None) == "recommender" if route_meta else False

    if needs_exit and not is_safe:
        return "block"
    if rec_data and routed_to_recommender:
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
    route_meta = state.get("route_metadata")
    focus_hint = getattr(route_meta, "focus_dimension", None) if route_meta else None

    current_dim = focus_hint
    if not current_dim:
        for dim in reversed(recommended_dims):
            dim_out = rec_data.get(dim)
            if dim_out and dim_out.items:
                current_dim = dim
                break
    if not current_dim:
        for dim, data in rec_data.items():
            if data.items:
                current_dim = dim
                break

    dim_data = rec_data.get(current_dim) if current_dim else None
    items = dim_data.items if dim_data else []
    strategy = dim_data.strategy if dim_data else ""
    tip = dim_data.tip if dim_data else ""

    item_lines = []
    for idx, item in enumerate(items, 1):
        rating = item.rating
        stars = "★" * int(rating) + ("☆" if rating - int(rating) >= 0.5 else "")
        item_lines.append(
            f"  [{idx}] {item.name} | 评分: {stars} {rating}/5\n"
            f"      亮点: {item.features}\n"
            f"      推荐理由: {item.reason}"
        )
    items_text = "\n".join(item_lines) if item_lines else "（暂无推荐项）"

    rec_failed = not items and ("失败" in strategy or "异常" in strategy)

    all_dims = list(rec_data.keys())
    remaining = [d for d in all_dims if d not in recommended_dims]
    remaining_labels = [_label_dim(d) for d in remaining]

    profile = state.get("user_profile")
    profile_text = profile.model_dump_json(indent=2, ensure_ascii=False) if profile else "暂无画像"

    return {
        "user_profile": profile_text,
        "focus_dimension": _label_dim(current_dim or "推荐"),
        "strategy": strategy,
        "recommendation_items": items_text,
        "tip": tip,
        "remaining_dimensions": "、".join(remaining_labels) if remaining_labels else "无（全部维度已完成）",
        "rec_failed": rec_failed,
    }


async def reply_node(state: TravelState) -> Dict[str, Any]:
    start_time = time.time()

    scenario = _detect_scenario(state)
    logger.info("Reply — scenario=%s", scenario)

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
        if ctx.get("rec_failed"):
            # Recommender 失败时直接使用 guide 模式降级，避免 LLM 根据旧数据编造推荐
            logger.warning("Reply — Recommender failed for %s, downgrading to guide", ctx["focus_dimension"])
            prompt_str = prompt.reply_guide_fallback.format(
                current_time=get_beijing_time_now(),
                focus_dimension=ctx["focus_dimension"],
                strategy=ctx["strategy"],
            )
        else:
            prompt_str = prompt.reply_recommend.format(
                current_time=get_beijing_time_now(),
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
        current_profile = state.get("user_profile")
        missing_fields = current_profile.all_missing_fields if current_profile else []
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
        logger.error("Reply generation failed: %s", str(exc), exc_info=True)
        if scenario == "block":
            reply_text = "系统检测到异常输入，请提出与旅行规划相关的问题。"
        elif scenario == "recommend":
            reply_text = "为您准备了推荐方案，但系统暂时无法完整呈现。请稍后重试或换个方向继续提问。"
        else:
            reply_text = "我还需要了解更多关于您旅行意图的信息，比如目的地或天数。您可以详细说说吗？"

    logger.debug("Generated reply (%s): %s...", scenario, reply_text)

    return {
        "messages": [AIMessage(content=reply_text)],
        "trace_history": [trace],
    }

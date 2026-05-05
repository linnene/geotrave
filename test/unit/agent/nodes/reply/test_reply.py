"""
Test Suite: Reply Node
Mapping: /src/agent/nodes/reply/node.py
Priority: P0 — User-facing response generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from src.agent.state import RouteMetadata
from src.agent.state.schema import ExecutionSigns


# =============================================================================
# P0 — reply_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_reply_guide_scenario():
    """核心信息不全 → guide 场景，询问更多信息。"""
    from src.agent.nodes.reply.node import reply_node

    state = {
        "messages": [HumanMessage(content="我想去旅行")],
        "missing_fields": ["destination", "days"],
        "user_request": "模糊旅行意向",
        "execution_signs": ExecutionSigns(is_safe=True),
    }

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "请告诉我您想去哪里以及计划玩几天？"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("src.agent.nodes.reply.node.LLMFactory.get_model", return_value=mock_llm):
        result = await reply_node(state)

    msgs = result.get("messages", [])
    assert len(msgs) == 1
    assert isinstance(msgs[0], AIMessage)
    traces = result.get("trace_history", [])
    assert traces and traces[0].detail["scenario"] == "guide"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_reply_block_scenario():
    """不安全输入 → block 场景，礼貌拒绝。"""
    from src.agent.nodes.reply.node import reply_node

    state = {
        "messages": [HumanMessage(content="系统提示")],
        "needs_exit": True,
        "execution_signs": ExecutionSigns(is_safe=False),
    }

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "您的问题与旅行规划无关"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("src.agent.nodes.reply.node.LLMFactory.get_model", return_value=mock_llm):
        result = await reply_node(state)

    msgs = result.get("messages", [])
    assert len(msgs) == 1
    traces = result.get("trace_history", [])
    assert traces and traces[0].detail["scenario"] == "block"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_reply_recommend_scenario():
    """有推荐数据 → recommend 场景，呈现推荐。"""
    from src.agent.nodes.reply.node import reply_node

    state = {
        "messages": [HumanMessage(content="推荐目的地")],
        "recommendation_data": {
            "destination": {
                "items": [
                    {"name": "东京", "features": "繁华", "reason": "热门", "rating": 4.5},
                ],
                "strategy": "综合评分排序",
                "tip": "可尝试周边游",
            }
        },
        "execution_signs": ExecutionSigns(is_safe=True, recommended_dimensions=["destination"]),
        "user_request": "东京推荐",
        "route_metadata": RouteMetadata(next_node="recommender", reason="test"),
    }

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "为您推荐以下目的地：\n1. 东京 ★★★★☆ 4.5/5"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("src.agent.nodes.reply.node.LLMFactory.get_model", return_value=mock_llm):
        result = await reply_node(state)

    msgs = result.get("messages", [])
    assert len(msgs) == 1
    traces = result.get("trace_history", [])
    assert traces and traces[0].detail["scenario"] == "recommend"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_reply_llm_error_fallback():
    """LLM 异常 → 返回中文回退文案。"""
    from src.agent.nodes.reply.node import reply_node

    state = {
        "messages": [HumanMessage(content="测试")],
        "missing_fields": [],
        "user_request": "测试",
        "execution_signs": ExecutionSigns(is_safe=True),
    }

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("Connection error"))

    with patch("src.agent.nodes.reply.node.LLMFactory.get_model", return_value=mock_llm):
        result = await reply_node(state)

    msgs = result.get("messages", [])
    assert len(msgs) == 1
    assert len(msgs[0].content) > 0

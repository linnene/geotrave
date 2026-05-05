"""
Test Suite: Analyst Node
Mapping: /src/agent/nodes/analyst/node.py
Priority: P0 — Requirement extraction gate
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import HumanMessage
from src.agent.state.schema import ExecutionSigns, UserProfile


# =============================================================================
# P0 — analyst_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_normal_extraction():
    """正常对话 → 提取 UserProfile，设置 is_core_complete。"""
    from src.agent.nodes.analyst.node import analyst_node

    state = {
        "messages": [HumanMessage(content="东京三日游")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{'
        '"updated_profile": {"destination": ["东京"], "days": 3}, '
        '"user_request": "东京三日游", '
        '"reason": "用户已有明确目的地和天数"'
        '}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert "user_profile" in result
    assert result["user_profile"].destination == ["东京"]
    assert result["user_profile"].days == 3
    assert result["execution_signs"].is_core_complete is True


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_missing_fields():
    """信息不足 → is_core_complete=False, missing_fields 非空。"""
    from src.agent.nodes.analyst.node import analyst_node

    state = {
        "messages": [HumanMessage(content="我想出去玩")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{'
        '"updated_profile": {"destination": [], "days": null}, '
        '"user_request": "模糊旅游意向", '
        '"reason": "用户未提供目的地和天数"'
        '}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert result["execution_signs"].is_core_complete is False
    assert len(result["missing_fields"]) > 0


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_incremental_merge():
    """增量合并 → 已有 profile 基础上追加新信息。"""
    from src.agent.nodes.analyst.node import analyst_node

    existing_profile = UserProfile(destination=["东京"], days=3)
    state = {
        "messages": [HumanMessage(content="预算5000")],
        "user_profile": existing_profile,
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{'
        '"updated_profile": {"destination": ["东京"], "days": 3, "budget_limit": 5000}, '
        '"user_request": "东京三日游，预算5000", '
        '"reason": "追加预算信息"'
        '}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert result["user_profile"].destination == ["东京"]
    assert result["user_profile"].budget_limit == 5000


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_llm_error_fallback():
    """LLM 异常 → 设置 is_core_complete=False，返回 trace。"""
    from src.agent.nodes.analyst.node import analyst_node

    state = {
        "messages": [HumanMessage(content="测试查询")],
    }

    mock_llm = MagicMock()
    mock_llm.bind.return_value.ainvoke = AsyncMock(side_effect=Exception("API timeout"))

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert result["execution_signs"].is_core_complete is False
    traces = result.get("trace_history", [])
    assert traces and traces[0].status == "FAIL"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_empty_state():
    """空消息 → 正常处理（Analyst 不负责状态守卫）。"""
    from src.agent.nodes.analyst.node import analyst_node

    state: dict = {}

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{'
        '"updated_profile": {"destination": [], "days": null}, '
        '"user_request": "", '
        '"reason": "无输入"'
        '}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert result["execution_signs"].is_core_complete is False


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_analyst_user_request_propagated():
    """提取的 user_request 正确写入 state。"""
    from src.agent.nodes.analyst.node import analyst_node

    state = {
        "messages": [HumanMessage(content="京都看红叶三天")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{'
        '"updated_profile": {"destination": ["京都"], "days": 3}, '
        '"user_request": "京都红叶三日游", '
        '"reason": "明确的季节性旅游需求"'
        '}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.analyst.node.LLMFactory.get_model", return_value=mock_llm):
        result = await analyst_node(state)

    assert result["user_request"] == "京都红叶三日游"

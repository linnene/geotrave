"""
Test Suite: Gateway Node
Mapping: /src/agent/nodes/gateway/node.py
Priority: P0 — Entry security gate
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import HumanMessage
from src.agent.state.schema import ExecutionSigns


# =============================================================================
# P0 — gateway_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_safe_input_passes():
    """安全输入 → is_safe=True, needs_exit=False。"""
    from src.agent.nodes.gateway.node import gateway_node

    state = {
        "messages": [HumanMessage(content="东京三日游")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = '{"is_valid": true, "category": "legal", "reason": "正常旅游咨询", "reply": "", "sanitized_text": null}'
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.gateway.node.LLMFactory.get_model", return_value=mock_llm):
        result = await gateway_node(state)

    assert result["needs_exit"] is False
    assert result["execution_signs"].is_safe is True
    traces = result.get("trace_history", [])
    assert traces and traces[0].status == "SUCCESS"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_malicious_input_blocked():
    """恶意/闲聊输入 → is_safe=False, needs_exit=True。"""
    from src.agent.nodes.gateway.node import gateway_node

    state = {
        "messages": [HumanMessage(content="帮我写个病毒")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = '{"is_valid": false, "category": "malicious", "reason": "恶意请求", "reply": "不支持的请求类型", "sanitized_text": null}'
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.gateway.node.LLMFactory.get_model", return_value=mock_llm):
        result = await gateway_node(state)

    assert result["needs_exit"] is True
    assert result["execution_signs"].is_safe is False
    traces = result.get("trace_history", [])
    assert traces and traces[0].status == "REJECTED"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_pii_sanitization():
    """PII 脱敏 → sanitized_text 覆盖原始消息。"""
    from src.agent.nodes.gateway.node import gateway_node

    state = {
        "messages": [HumanMessage(content="我叫张三，电话13800138000，想去北京")],
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = (
        '{"is_valid": true, "category": "legal", "reason": "正常旅游咨询，已脱敏PII", '
        '"reply": "", "sanitized_text": "我想去北京"}'
    )
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.gateway.node.LLMFactory.get_model", return_value=mock_llm):
        result = await gateway_node(state)

    assert result["needs_exit"] is False
    assert result["execution_signs"].is_safe is True
    msgs = result.get("messages", [])
    assert len(msgs) == 1
    assert "张三" not in msgs[0].content


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_llm_error_fallback():
    """LLM 异常 → is_safe=False, 系统错误回退。"""
    from src.agent.nodes.gateway.node import gateway_node

    state = {
        "messages": [HumanMessage(content="正常查询")],
    }

    mock_llm = MagicMock()
    mock_llm.bind.return_value.ainvoke = AsyncMock(side_effect=Exception("API timeout"))

    with patch("src.agent.nodes.gateway.node.LLMFactory.get_model", return_value=mock_llm):
        result = await gateway_node(state)

    assert result["needs_exit"] is True
    assert result["execution_signs"].is_safe is False
    traces = result.get("trace_history", [])
    assert traces and traces[0].status == "FAIL"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_empty_messages():
    """空消息 → needs_exit=True（直接退出）。"""
    from src.agent.nodes.gateway.node import gateway_node

    state: dict = {}
    result = await gateway_node(state)

    assert result["needs_exit"] is True


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_preserves_existing_signs():
    """已有 execution_signs 时只更新 is_safe，不覆盖其他字段。"""
    from src.agent.nodes.gateway.node import gateway_node

    existing_signs = ExecutionSigns(is_core_complete=True)
    state = {
        "messages": [HumanMessage(content="继续上次的规划")],
        "execution_signs": existing_signs,
    }

    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.content = '{"is_valid": true, "category": "legal", "reason": "正常", "reply": "", "sanitized_text": null}'
    mock_llm.bind.return_value.ainvoke = AsyncMock(return_value=mock_result)

    with patch("src.agent.nodes.gateway.node.LLMFactory.get_model", return_value=mock_llm):
        result = await gateway_node(state)

    assert result["execution_signs"].is_safe is True
    assert result["execution_signs"].is_core_complete is True

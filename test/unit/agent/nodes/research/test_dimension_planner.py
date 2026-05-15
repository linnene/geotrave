"""
Test Suite: DimensionPlanner Node
Mapping: /src/agent/nodes/research/dimension_planner/node.py
Priority: P0 — Phase 7 node decomposing research into parallel dimensions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import ExecutionSigns, RouteMetadata


# =============================================================================
# P0 — dimension_planner_node core logic
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_normal_split():
    """LLM returns valid dimensions → planned_dimensions + dimension_hints written."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "messages": [],
        "user_profile": None,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"food","focus":"美食推荐","priority":5},{"name":"attraction","focus":"景点","priority":4}],"rationale":"test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await dimension_planner_node(state)

    assert "planned_dimensions" in result
    assert result["planned_dimensions"] == ["food", "attraction"]
    assert result["dimension_hints"] == {"food": "美食推荐", "attraction": "景点"}
    assert len(result["trace_history"]) == 1
    assert result["trace_history"][0].status == "SUCCESS"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_caps_at_3():
    """LLM returns 5 dimensions → capped at 3, sorted by priority descending."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "messages": [],
        "user_profile": None,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"a","focus":"a","priority":1},{"name":"b","focus":"b","priority":2},{"name":"c","focus":"c","priority":3},{"name":"d","focus":"d","priority":5},{"name":"e","focus":"e","priority":4}],"rationale":"test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await dimension_planner_node(state)

    assert len(result["planned_dimensions"]) == 3
    assert result["planned_dimensions"] == ["d", "e", "c"]


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_manager_preset_short_circuit():
    """Manager pre-set focus_dimension → skip LLM entirely."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "focus_dimension": "hot_spring",
        "messages": [],
    }

    result = await dimension_planner_node(state)

    assert result["planned_dimensions"] == ["hot_spring"]
    assert result["dimension_hints"] == {"hot_spring": "hot_spring相关信息"}
    assert result["trace_history"][0].status == "SUCCESS"
    assert result["trace_history"][0].detail["rationale"] == "Manager pre-set dimension (coverage gap fill)"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_no_focus_dimension_no_short_circuit():
    """focus_dimension absent or None → proceed to LLM analysis."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "focus_dimension": None,
        "messages": [],
        "user_profile": None,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"general","focus":"综合信息","priority":3}],"rationale":"test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await dimension_planner_node(state)

    assert result["planned_dimensions"] == ["general"]


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_llm_failure_fallback():
    """LLM exception → fallback to ['attraction', 'general']."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "messages": [],
        "user_profile": None,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = Exception("LLM timeout")
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await dimension_planner_node(state)

    assert result["planned_dimensions"] == ["attraction", "general"]
    assert result["dimension_hints"] == {"attraction": "主要景点", "general": "综合信息"}
    assert result["trace_history"][0].status == "FAIL"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_dimension_planner_single_dimension():
    """LLM returns a single dimension → planned_dimensions has exactly 1 item."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    state = {
        "messages": [],
        "user_profile": None,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"ski_resort","focus":"滑雪场推荐","priority":4}],"rationale":"single dimension test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await dimension_planner_node(state)

    assert result["planned_dimensions"] == ["ski_resort"]
    assert result["dimension_hints"] == {"ski_resort": "滑雪场推荐"}


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_dimension_planner_includes_destination_in_prompt():
    """UserProfile with destination → destination_context injected into prompt."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node
    from src.agent.state.schema import UserProfile

    profile = UserProfile(destination=["东京"])
    state = {
        "messages": [],
        "user_profile": profile,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"attraction","focus":"东京景点","priority":4}],"rationale":"test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        await dimension_planner_node(state)

    call_args = mock_chain.ainvoke.call_args[0][0]
    assert "东京" in call_args


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_dimension_planner_passes_manager_hint():
    """RouteMetadata.reason → injected as manager_hint in prompt."""
    from src.agent.nodes.research.dimension_planner.node import dimension_planner_node

    route = RouteMetadata(next_node="research_loop", reason="覆盖度不足，补充餐饮维度")
    state = {
        "messages": [],
        "user_profile": None,
        "route_metadata": route,
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = MagicMock(content='{"dimensions":[{"name":"food","focus":"餐饮推荐","priority":4}],"rationale":"test"}')
    mock_llm.bind.return_value = mock_chain
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.research.dimension_planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        await dimension_planner_node(state)

    call_args = mock_chain.ainvoke.call_args[0][0]
    assert "覆盖度不足" in call_args

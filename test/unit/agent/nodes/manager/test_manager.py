"""
Test Suite: Manager Node
Mapping: /src/agent/nodes/manager/node.py
Priority: P0 — Central routing brain
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state.schema import ExecutionSigns, ResearchManifest, ResearchLoopInternal, UserSelections


# =============================================================================
# P0 — manager_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_routes_to_research_loop():
    """is_core_complete=True, 无推荐无计划 → research_loop。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=True, is_safe=True)
    manifest = ResearchManifest()
    state = {
        "execution_signs": signs,
        "messages": [],
                "research_data": manifest,
    }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(return_value={
        "next_stage": "research_loop",
        "rationale": "需要调研目的地信息",
        "user_selections": None,
        "focus_dimension": None,
    })

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    assert result["route_metadata"].next_node == "research_loop"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_routes_to_recommender():
    """有 research_hashes, 无推荐数据 → recommender。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=True, is_safe=True)
    manifest = ResearchManifest(research_hashes={"query1": ["hash_abc"]})
    state = {
        "execution_signs": signs,
        "messages": [],
                "research_data": manifest,
    }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(return_value={
        "next_stage": "recommender",
        "rationale": "调研充分，开始推荐",
        "user_selections": None,
        "focus_dimension": "destination",
    })

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    assert result["route_metadata"].next_node == "recommender"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_hard_guard_core_incomplete():
    """is_core_complete=False → LLM 决策被覆写为 reply。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=False, is_safe=True)
    state = {
        "execution_signs": signs,
        "messages": [],
            }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(return_value={
        "next_stage": "research_loop",
        "rationale": "LLM 认为可以调研",
        "user_selections": None,
        "focus_dimension": None,
    })

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    assert result["route_metadata"].next_node == "reply"
    assert "硬守卫覆写" in result["route_metadata"].reason


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_needs_reselect_blocks_planner():
    """needs_reselect=True → 禁止路由到 planner。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=True, is_safe=True)
    state = {
        "execution_signs": signs,
        "messages": [],
                "user_selections": UserSelections(needs_reselect=True, reselection_feedback="太贵了"),
    }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(return_value={
        "next_stage": "planner",
        "rationale": "LLM 试图规划",
        "user_selections": None,
        "focus_dimension": None,
    })

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    assert result["route_metadata"].next_node == "recommender"
    assert "硬守卫覆写" in result["route_metadata"].reason


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_llm_error_fallback():
    """LLM 异常 → fallback 到 reply（is_core_complete=False 时）或 research_loop。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=True, is_safe=True)
    state = {
        "execution_signs": signs,
        "messages": [],
            }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(side_effect=Exception("API error"))

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    assert result["route_metadata"].next_node == "research_loop"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_resets_research_state_on_loop():
    """路由到 research_loop → 重置 loop_state。"""
    from src.agent.nodes.manager.node import manager_node

    signs = ExecutionSigns(is_core_complete=True, is_safe=True)
    old_loop = ResearchLoopInternal(loop_iteration=3, continue_loop=False)
    manifest = ResearchManifest(loop_state=old_loop)
    state = {
        "execution_signs": signs,
        "messages": [],
                "research_data": manifest,
    }

    mock_llm = MagicMock()
    mock_llm.__or__.return_value.ainvoke = AsyncMock(return_value={
        "next_stage": "research_loop",
        "rationale": "新一轮调研",
        "user_selections": None,
        "focus_dimension": None,
    })

    with patch("src.agent.nodes.manager.node.LLMFactory.get_model", return_value=mock_llm):
        result = await manager_node(state)

    new_manifest = result["research_data"]
    assert new_manifest.loop_state.loop_iteration == 0

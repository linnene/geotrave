"""
Test Suite: Planner Node
Mapping: /src/agent/nodes/planner/node.py
Priority: P0 — Delivery node producing day-by-day itinerary
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import ExecutionSigns, ResearchManifest
from src.agent.state.schema import CriticResult, ResearchLoopInternal


# =============================================================================
# P0 — planner_node full pipeline
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_planner_produces_output():
    """Mock LLM returns valid itinerary → PlannerOutput written to state."""
    from src.agent.nodes.planner.node import planner_node

    loop_state = ResearchLoopInternal(
        all_passed_results=[
            CriticResult(
                query="东京景点",
                tool_name="spatial_search",
                safety_tag="safe",
                relevance_score=90.0,
                utility_score=85.0,
                rationale="浅草寺、晴空塔等核心景点信息",
            ),
        ]
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "recommendation_data": {
            "destination": {"dimension": "destination", "items": [{"name": "东京", "features": "...", "reason": "经典目的地", "rating": 4.5}], "strategy": "test", "tip": "..."},
        },
        "messages": [],
        "user_request": "东京三日游",
        "execution_signs": ExecutionSigns(is_core_complete=True, is_recommendation_complete=True),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "days": [
            {
                "day": 1,
                "date": "2026-05-02",
                "activities": [
                    {
                        "time": "09:00-11:30",
                        "place": "浅草寺",
                        "type": "attraction",
                        "description": "参观东京最古老的寺庙",
                        "duration_min": 150,
                        "transport": None,
                    },
                    {
                        "time": "12:00-13:00",
                        "place": "浅草拉面店",
                        "type": "dining",
                        "description": "午餐",
                        "duration_min": 60,
                        "transport": "步行",
                    },
                ],
            },
            {
                "day": 2,
                "activities": [
                    {
                        "time": "10:00-12:00",
                        "place": "晴空塔",
                        "type": "attraction",
                        "description": "东京地标观景",
                        "duration_min": 120,
                        "transport": None,
                    },
                ],
            },
        ],
        "total_budget_estimate": "约 5000 元/人",
        "notes": ["雨天备选：东京国立博物馆"],
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await planner_node(state)

    assert "plan_data" in result
    plan = result["plan_data"]
    assert len(plan["days"]) == 2
    assert plan["days"][0]["day"] == 1
    assert plan["days"][0]["date"] == "2026-05-02"
    assert len(plan["days"][0]["activities"]) == 2
    assert plan["days"][0]["activities"][0]["place"] == "浅草寺"
    assert plan["days"][0]["activities"][1]["type"] == "dining"
    assert plan["total_budget_estimate"] == "约 5000 元/人"
    assert "雨天备选" in plan["notes"][0]


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_planner_writes_state():
    """plan_data is written to result dict."""
    from src.agent.nodes.planner.node import planner_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "test",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "days": [],
        "notes": ["无足够数据生成行程"],
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await planner_node(state)

    assert "plan_data" in result
    assert result["plan_data"]["notes"][0] == "无足够数据生成行程"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_planner_sets_complete_flag():
    """is_plan_complete set to True after successful execution."""
    from src.agent.nodes.planner.node import planner_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "test",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "days": [],
        "notes": [],
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await planner_node(state)

    assert result["execution_signs"].is_plan_complete is True


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_planner_llm_error_graceful():
    """LLM exception → graceful fallback with empty plan."""
    from src.agent.nodes.planner.node import planner_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "test",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = Exception("LLM rate limit exceeded")
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await planner_node(state)

    assert "plan_data" in result
    assert "失败" in result["plan_data"]["notes"][0]
    assert result["execution_signs"].is_plan_complete is True


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_planner_multiple_days():
    """Multi-day itinerary with activities correctly handled."""
    from src.agent.nodes.planner.node import planner_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "七日游",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "days": [{"day": i, "activities": []} for i in range(1, 8)],
        "notes": [],
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.planner.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await planner_node(state)

    assert len(result["plan_data"]["days"]) == 7

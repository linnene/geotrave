"""
Test Suite: Recommender Node
Mapping: /src/agent/nodes/recommender/node.py
Priority: P0 — Single-dimension recommendation delivery node
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import ExecutionSigns, ResearchManifest
from src.agent.state.schema import CriticResult, ResearchLoopInternal


# =============================================================================
# P0 — recommender_node single-dimension pipeline
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_single_dimension_output():
    """First call with no prior dimensions → focuses on destination, accumulates by dimension."""
    from src.agent.nodes.recommender.node import recommender_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
        "execution_signs": ExecutionSigns(recommended_dimensions=[]),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "dimension": "destination",
        "items": [
            {"name": "东京", "features": "国际化大都市", "reason": "经典目的地", "rating": 4.5},
        ],
        "strategy": "推荐东京作为首选目的地",
        "tip": "选定目的地后我帮您挑住宿",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    rec_data = result["recommendation_data"]
    assert isinstance(rec_data, dict)
    assert "destination" in rec_data
    assert rec_data["destination"]["dimension"] == "destination"
    assert len(rec_data["destination"]["items"]) == 1
    assert rec_data["destination"]["items"][0]["name"] == "东京"
    assert rec_data["destination"]["items"][0]["rating"] == 4.5

    # Should append dimension, NOT set is_recommendation_complete
    signs = result["execution_signs"]
    assert signs.is_recommendation_complete is False
    assert signs.recommended_dimensions == ["destination"]


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_second_dimension():
    """Second call → focuses on accommodation, accumulates without overwriting."""
    from src.agent.nodes.recommender.node import recommender_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
        "execution_signs": ExecutionSigns(recommended_dimensions=["destination"]),
        "recommendation_data": {
            "destination": {"dimension": "destination", "items": [{"name": "东京", "features": "...", "reason": "...", "rating": 4.5}], "strategy": "...", "tip": "..."},
        },
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "dimension": "accommodation",
        "items": [
            {"name": "浅草民宿", "features": "交通便利", "reason": "靠近浅草寺", "rating": 4.0},
        ],
        "strategy": "优先推荐浅草周边住宿",
        "tip": "有中意的住宿吗？下一步帮您规划行程",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    rec_data = result["recommendation_data"]
    assert "destination" in rec_data  # preserved
    assert "accommodation" in rec_data  # new
    assert len(rec_data["destination"]["items"]) == 1
    assert len(rec_data["accommodation"]["items"]) == 1
    assert rec_data["accommodation"]["items"][0]["name"] == "浅草民宿"

    signs = result["execution_signs"]
    assert signs.recommended_dimensions == ["destination", "accommodation"]
    assert signs.is_recommendation_complete is False


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_all_dimensions_covered():
    """All 3 dimensions already covered → short-circuit with is_recommendation_complete=True."""
    from src.agent.nodes.recommender.node import recommender_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
        "execution_signs": ExecutionSigns(
            recommended_dimensions=["destination", "accommodation", "dining"]
        ),
    }

    result = await recommender_node(state)

    # Should return immediately without LLM call
    assert result["execution_signs"].is_recommendation_complete is True


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_recommender_empty_research_data():
    """No research data → node still runs, produces empty recommendations for the focus dimension."""
    from src.agent.nodes.recommender.node import recommender_node

    state = {
        "research_data": None,
        "messages": [],
        "user_request": "test",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "dimension": "destination",
        "items": [],
        "strategy": "研究数据为空，无法推荐",
        "tip": "请先完善研究数据",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    assert "recommendation_data" in result
    assert "destination" in result["recommendation_data"]
    assert result["recommendation_data"]["destination"]["items"] == []
    assert result["execution_signs"].recommended_dimensions == ["destination"]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_recommender_llm_error_graceful():
    """LLM exception → graceful fallback with empty items and error strategy."""
    from src.agent.nodes.recommender.node import recommender_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "test",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.side_effect = Exception("LLM connection timeout")
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    rec_data = result["recommendation_data"]
    dim = list(rec_data.keys())[0]
    assert "失败" in rec_data[dim]["strategy"]
    assert rec_data[dim]["items"] == []

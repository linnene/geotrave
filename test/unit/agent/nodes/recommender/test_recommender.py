"""
Test Suite: Recommender Node
Mapping: /src/agent/nodes/recommender/node.py
Priority: P0 — Delivery node producing destination/accommodation/dining recommendations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import ExecutionSigns, ResearchManifest
from src.agent.state.schema import CriticResult, ResearchLoopInternal


# =============================================================================
# P0 — recommender_node full pipeline
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_produces_output():
    """Mock LLM returns valid recommendation data → RecommenderOutput written to state."""
    from src.agent.nodes.recommender.node import recommender_node

    loop_state = ResearchLoopInternal(
        all_passed_results=[
            CriticResult(
                query="东京酒店推荐",
                tool_name="spatial_search",
                safety_tag="safe",
                relevance_score=85.0,
                utility_score=90.0,
                rationale="覆盖了浅草地区的酒店信息",
            ),
        ]
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
        "execution_signs": ExecutionSigns(is_core_complete=True),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "destinations": [
            {"name": "东京", "type": "destination", "score": 90, "rationale": "经典目的地"},
        ],
        "accommodations": [
            {"name": "浅草民宿", "type": "accommodation", "score": 85, "rationale": "交通便利"},
        ],
        "dining": [
            {"name": "银座寿司店", "type": "dining", "score": 80, "rationale": "新鲜食材"},
        ],
        "strategy": "优先推荐浅草/上野周边住宿，兼顾交通和性价比",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    assert "recommendation_data" in result
    rec = result["recommendation_data"]
    assert len(rec["destinations"]) == 1
    assert rec["destinations"][0]["name"] == "东京"
    assert len(rec["accommodations"]) == 1
    assert len(rec["dining"]) == 1
    assert "优先推荐" in rec["strategy"]


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_writes_state():
    """recommendation_data is written to result dict."""
    from src.agent.nodes.recommender.node import recommender_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "京都旅行",
        "execution_signs": ExecutionSigns(),
    }

    mock_llm = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = {
        "destinations": [],
        "accommodations": [],
        "dining": [],
        "strategy": "无足够数据",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    assert result["recommendation_data"]["strategy"] == "无足够数据"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_recommender_sets_complete_flag():
    """is_recommendation_complete set to True after successful execution."""
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
    mock_chain.ainvoke.return_value = {
        "destinations": [],
        "accommodations": [],
        "dining": [],
        "strategy": "test",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    assert result["execution_signs"].is_recommendation_complete is True


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_recommender_empty_research_data():
    """No research data → node still runs, produces empty recommendations."""
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
        "destinations": [],
        "accommodations": [],
        "dining": [],
        "strategy": "研究数据为空，无法推荐",
    }
    mock_llm.__or__.return_value = mock_chain

    with patch(
        "src.agent.nodes.recommender.node.LLMFactory.get_model",
        return_value=mock_llm,
    ):
        result = await recommender_node(state)

    assert "recommendation_data" in result
    assert result["execution_signs"].is_recommendation_complete is True


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_recommender_llm_error_graceful():
    """LLM exception → graceful fallback with empty recommendations."""
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

    assert "recommendation_data" in result
    assert "失败" in result["recommendation_data"]["strategy"]
    assert result["execution_signs"].is_recommendation_complete is True

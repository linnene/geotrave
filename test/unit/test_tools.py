import pytest
from unittest.mock import AsyncMock, patch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
from agent.nodes.researcher.tools import ResearcherTools
from agent.schema import ResearchPlan

@pytest.mark.asyncio
async def test_weather_api_integration():
    result = await ResearcherTools.search_weather_openmeteo("大理", "2026-05-01", "2026-05-05")
    assert len(result) == 1
    assert "Weather for 大理" in result[0]["title"]
    assert "Forecast for 2026-05-01" in result[0]["content"]

@pytest.mark.asyncio
async def test_web_search_ddg_resilience():
    result = await ResearcherTools.search_web_ddg("大理 攻略")
    assert len(result) == 1
    assert "Web Result: Scenic spots in 大理 攻略" in result[0]["title"]
    assert result[0]["source"] == "web"

@pytest.mark.asyncio
async def test_vector_db_retrieval():
    result = await ResearcherTools.search_local_kt("大理 景点")
    assert len(result) == 1
    assert "Local Tips for 大理 景点" in result[0]["title"]
    assert result[0]["source"] == "local_kb"

@pytest.mark.asyncio
async def test_researcher_plan_generation_logic():
    state = {"user_profile": {"destination": ["大理"], "days": 5}, "messages": []}
    mock_plan = ResearchPlan(local_query="大理 攻略", web_queries=["大理 景点"], need_weather=True)
    with patch("agent.nodes.researcher.tools.PydanticOutputParser") as mock_parser_class:
        with patch("agent.nodes.researcher.tools.research_query_prompt_template"):
            mock_llm = AsyncMock()
            mock_chain = AsyncMock()
            mock_chain.ainvoke.return_value = mock_plan
            mock_llm.__or__.return_value = mock_chain
            plan = await ResearcherTools.generate_research_plan(state, mock_llm)
            assert plan is not None
            assert plan.local_query == "大理 攻略"
            assert plan.need_weather is True

@pytest.mark.asyncio
async def test_researcher_filter_logic_item():
    items = [{"title": "大理攻略", "content": "大理好玩", "metadata": {"query": "大理"}}, {"title": "抽奖", "content": "中大奖", "metadata": {"query": "大理"}}]
    filtered = await ResearcherTools.filter_retrieval_items(items, None)
    assert len(filtered) == 2

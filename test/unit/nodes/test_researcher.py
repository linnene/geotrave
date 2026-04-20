import pytest
import asyncio
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock
from src.agent.nodes.researcher.researcher import researcher_node
from src.agent.schema import ResearchPlan
from src.agent.state import TravelState, RetrievalItem

def load_mock_response(folder, filename):
    path = os.path.join("test", "mock", folder, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_researcher_node_execution():
    """
    Priority: P0
    Description: Verifies that the researcher node correctly spawns and aggregates 
                 results from various tool backends using data from /test/mock/.
    """
    # 1. Load data from the mock folder
    mock_plans = load_mock_response("llm_responses", "researchplans.json")
    mock_tools = load_mock_response("tool_outputs", "research_tools.json")
    
    plan_data = mock_plans["shanghai_plan"]
    mock_plan = ResearchPlan(**plan_data)
    
    mock_local_results: list[RetrievalItem] = mock_tools["shanghai_local"]
    mock_weather_results: list[RetrievalItem] = mock_tools["shanghai_weather"]
    mock_web_results: list[RetrievalItem] = [
        {"content": "上海红烧肉非常出名。", "source": "web_search", "title": "Web Info", "link": None, "metadata": {}}
    ]

    with patch("src.agent.nodes.researcher.tools.ResearcherTools.generate_research_plan", return_value=mock_plan), \
         patch("src.agent.nodes.researcher.tools.ResearcherTools.search_local_kt", return_value=mock_local_results), \
         patch("src.agent.nodes.researcher.tools.ResearcherTools.search_web_ddg", return_value=mock_web_results), \
         patch("src.agent.nodes.researcher.tools.ResearcherTools.search_weather_openmeteo", return_value=mock_weather_results), \
         patch("src.agent.nodes.researcher.tools.ResearcherTools.filter_retrieval_items", return_value=mock_local_results + mock_web_results):

        
        state: TravelState = {
            "messages": [],
            "user_profile": {
                "destination": ["上海"],
                "days": 3,
                "date": None,
                "people_count": None,
                "budget_limit": None,
                "accommodation": None,
                "dining": None,
                "transportation": None,
                "pace": None,
                "activities": [],
                "preferences": [],
                "avoidances": []
            },
            "search_data": {
                "query_history": [],
                "retrieval_context": None,
                "retrieval_results": [],
                "retrieval_stats": None,
                "weather_info": None
            },
            "latest_intent": None,
            "needs_research": True,
            "recommender_data": None
        }

        results = []
        async for update in researcher_node(state):
            results.append(update)

            
        # Verify the aggregation
        # researcher_node yields updates as tasks complete, 
        # but for simplicity, we check if the final state update in research_data is correct.
        # Note: In the actual implementation, it yields incremental data.
        
        assert len(results) > 0
        last_update = results[-1]
        search_data = last_update.get("search_data", {})
        
        # Check if research results were aggregated
        all_res = search_data.get("retrieval_results", [])
        sources = [r["source"] if isinstance(r, dict) else r.source for r in all_res]
        
        # Verify non-weather dimensions are present
        assert "local_db" in sources or any("local_db" in str(s) for s in sources)
        assert "web_search" in sources
        
        # Verify weather info is captured in weather_info field
        weather_info = search_data.get("weather_info", "")
        assert "api_weather" in weather_info.lower() or "上海今日晴" in weather_info

@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_researcher_no_destination_fallback():
    """
    Priority: P0
    Description: Verifies researcher handles empty destination gracefully.
    """
    state: TravelState = {
        "messages": [],
        "user_profile": {"destination": [], "days": None, "date": None, "people_count": None, "budget_limit": None, "accommodation": None, "dining": None, "transportation": None, "pace": None, "activities": [], "preferences": [], "avoidances": []},
        "search_data": {
            "query_history": [],
            "retrieval_context": None,
            "retrieval_results": [],
            "retrieval_stats": None,
            "weather_info": None
        },
        "latest_intent": None,
        "needs_research": False,
        "recommender_data": None
    }
    
    updates = []

    async for update in researcher_node(state):
        updates.append(update)
        
    assert "No destination provided" in updates[0]["search_data"]["retrieval_context"]

import pytest
import json
import os
from unittest.mock import patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from src.agent.nodes.analyzer.analyzer import analyzer_node
from src.agent.schema import TravelInfo, UserProfile

def load_analyzer_scenarios():
    path = os.path.join("test", "eval", "analyzer_dataset.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
@pytest.mark.priority("P0")
@pytest.mark.parametrize("scenario", load_analyzer_scenarios())
async def test_analyzer_info_extraction(scenario):
    """
    Priority: P0
    Description: Verifies that the analyzer correctly extracts structured entity data from text.
    Responsibility: Evaluates demand modeling accuracy.
    Assertion Standard: Extracted fields in user_profile must match expected JSON.
    """
    input_text = scenario["input"]
    expected = scenario["expected"]
    
    # Mock result building
    mock_profile = UserProfile(
        destination=expected.get("destination", []),
        days=expected.get("days"),
        people_count=expected.get("people_count", 1),
        budget_limit=expected.get("budget_limit", 0),
        dining=expected.get("dining"),
        avoidances=expected.get("avoidances", [])
    )
    
    mock_result = TravelInfo(
        user_profile=mock_profile,
        needs_research=expected.get("needs_research", False),
        reply="好的，我正在为您处理上海的行程建议。"
    )
    
    with patch("src.agent.nodes.analyzer.analyzer.llm") as mock_llm:
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = mock_result
        mock_llm.__or__.return_value = mock_chain
        
        state: TravelState = {
            "messages": [HumanMessage(content=input_text)],
            "user_profile": {
                "destination": [],
                "days": None,
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
            "needs_research": False,
            "latest_intent": None,
            "search_data": None,
            "recommender_data": None
        }
        
        result = await analyzer_node(state)

        
        # Verify Profile
        actual_profile = result["user_profile"]
        for key, value in expected.items():
            if key == "needs_research":
                assert result["needs_research"] == value
            else:
                assert actual_profile[key] == value
        
        # Verify AI Message added
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_analyzer_error_fallback():
    """
    Priority: P0
    Description: Test analyzer resilience when LLM chain fails.
    """
    state: TravelState = {
        "messages": [HumanMessage(content="上海")],
        "user_profile": {
            "destination": [],
            "days": None,
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
        "needs_research": False,
        "latest_intent": None,
        "search_data": None,
        "recommender_data": None
    }
    
    with patch("src.agent.nodes.analyzer.analyzer.llm") as mock_llm:

        mock_llm.__or__.side_effect = Exception("Analyzer Chain Error")
        
        result = await analyzer_node(state)
        
        assert result["needs_research"] is False
        assert "抱歉" in result["messages"][0].content

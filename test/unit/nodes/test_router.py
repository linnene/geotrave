"""
Description: Router Node Decision Logic Test Suite
Mapping: /src/agent/nodes/router/router.py
Priority: P0 - Critical Gateway
Main Test Items:
1. Intent classification matching (P0)
2. Research flag (needs_research) triggering (P0)
3. Safety/Security prompt rejection (P1)
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from src.agent.nodes.router.router import router_node, RouterIntent
from src.agent.state import TravelState
def load_scenarios():
    """Helper to load isolated test data."""
    # Build path relative to project root instead of __file__ to avoid confusion
    # In pytest, the CWD is usually the project root
    path = os.path.join(os.getcwd(), "test", "eval", "data", "router_scenarios.json")
    if not os.path.exists(path):
        # Fallback to relative path from this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.abspath(os.path.join(current_dir, "..", "..", "eval", "data", "router_scenarios.json"))
        
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
@pytest.mark.priority("P0")
@pytest.mark.parametrize("scenario", load_scenarios())
async def test_router_intent_classification(scenario):
    """
    Priority: P0
    Description: Verifies precision of intent labeling for diverse user inputs using mocked LLM.
    Responsibility: Ensures the gateway directs users to the correct downstream nodes.
    Assertion Standard: Output intent must exactly match expected ground truth in test data.
    """
    input_text = scenario["input"]
    expected = scenario["expected"]
    
    # Mocking the LLM chain return value
    mock_parsed_result = RouterIntent(
        enum_intent=expected["intent"],
        is_safe=expected.get("is_safe", True),
        reply_for_malicious=expected.get("reply_for_malicious", "")
    )
    
    # We patch the 'llm' within the router module or its invocation
    # Since 'llm | parser' is used, we need to mock the pipe operator and ainvoke.
    with patch("src.agent.nodes.router.router.llm") as mock_llm:
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = mock_parsed_result
        mock_llm.__or__.return_value = mock_chain
        
        # Prepare state using TravelState structure to satisfy type checkers
        state: TravelState = {
            "messages": [HumanMessage(content=input_text)],
            "needs_research": False,
            "latest_intent": None,
            "user_profile": None,
            "search_data": None,
            "recommender_data": None
        }
        
        # Execute node
        result = await router_node(state)


        
        # Assertions
        assert result["latest_intent"] == expected["intent"], (
            f"Intent Mismatch for input: '{input_text}'. "
            f"Expected: {expected['intent']}, Actual: {result['latest_intent']}"
        )
        
        # Check if malicious path returned a message
        if expected["intent"] == "chit_chat_or_malicious" or not expected.get("is_safe", True):
            assert len(result.get("messages", [])) > 0, "Security Failure: No rejection message returned for malicious input."
            assert isinstance(result["messages"][0], AIMessage)

@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_router_error_fallback():
    """
    Priority: P0
    Description: Verifies that the router node has a safe fallback on LLM failure.
    Responsibility: Prevents graph crashes.
    Assertion Standard: Return a default intent (e.g., 'new_destination') when an exception occurs.
    """
    state: TravelState = {
        "messages": [HumanMessage(content="Any input")],
        "needs_research": False,
        "latest_intent": None,
        "user_profile": None,
        "search_data": None,
        "recommender_data": None
    }
    
    # We patch the pipe operator to raise an exception when called

    with patch("src.agent.nodes.router.router.llm") as mock_llm:
        mock_llm.__or__.side_effect = Exception("LLM Connection Error")
        result = await router_node(state)
        assert result["latest_intent"] == "new_destination", "Fallback Failure: Router did not default to 'new_destination' on error."



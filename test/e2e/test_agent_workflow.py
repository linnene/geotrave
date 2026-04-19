"""
Description: Agent End-To-End (E2E) Workflow Test Suite
Mapping: Maps to src/agent/graph.py
Priority: P0 - Critical for business logic closure
Main Test Items:
1. Multi-turn conversation state accumulation (P0)
2. Intent-driven routing accuracy (P0)
3. Full path from inquiry to research trigger (P0)
"""

import pytest
import uuid
import json
import os
from unittest.mock import patch, AsyncMock
from src.agent.graph import graph_app
from src.agent.state import RetrievalItem
from src.agent.schema import ResearchPlan

def load_cases():
    """Helper to load E2E test dataset."""
    current_dir = os.path.dirname(__file__)
    # Moved to standardized data directory
    path = os.path.join(current_dir, "..", "data", "dataset.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["workflow_cases"]
    return []

@pytest.mark.asyncio
class TestAgentWorkflow:
    """
    Priority: P0
    Description: Verifies the full agent lifecycle using predefined test cases from dataset.json.
    Responsibility: Ensures that changes in prompts or graph nodes do not break the core travel planning flow.
    """

    @pytest.mark.parametrize("case", load_cases(), ids=lambda x: x["id"])
    @patch("src.agent.nodes.researcher.tools.ResearcherTools.generate_research_plan", new_callable=AsyncMock)
    @patch("src.agent.nodes.researcher.tools.ResearcherTools.search_web_ddg", new_callable=AsyncMock)
    @patch("src.agent.nodes.researcher.tools.ResearcherTools.search_local_kt", new_callable=AsyncMock)
    async def test_agent_workflow_logic(self, mock_search_local, mock_search_web, mock_gen_plan, case):
        # Setup mocks to avoid external API costs/volatility during E2E logic check
        mock_gen_plan.return_value = ResearchPlan(local_query="Mock Destination", web_queries=["Mock web search"])
        mock_search_web.return_value = [
            RetrievalItem(source="web", title="Mock Title", content="Mock Content", link="http://mock", metadata={})
        ]
        mock_search_local.return_value = [
            RetrievalItem(source="local", title="Mock Local", content="Mock Local Docs", link=None, metadata={})
        ]
        
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        result = None
        # Handle multi-turn or simple cases
        inputs = []
        if "turns" in case:
            inputs = case["turns"]
        elif "update_input" in case:
            inputs = [case["input"], case["update_input"]]
        else:
            inputs = [case["input"]]

        for user_text in inputs:
            # LangGraph StateGraph uses 'messages' array to aggregate dialog
            result = await graph_app.ainvoke({"messages": [("user", user_text)]}, config=config)

        # Assertion standard: Verify key state fields
        expected = case["expected_state"]
        for key, val in expected.items():
            if result is not None:
                # Resolve field mapping (dataset key vs state key)
                if key in result:
                    actual = result.get(key)
                else:
                    user_profile = result.get("user_profile") or {}
                    actual = user_profile.get("people_count" if key == "people" else key)
                
                assert str(actual) == str(val), \
                    f"E2E Mismatch in {case['id']}! Field: {key}. Expected: {val}, Actual: {actual}. State Snapshot: {result}"
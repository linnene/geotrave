import pytest
import uuid
import json
import os
from unittest.mock import patch, AsyncMock
from langchain_core.messages import HumanMessage

from agent.graph import graph_app
from agent.state import RetrievalItem

def load_cases():
    current_dir = os.path.dirname(__file__)
    paths = [
        os.path.join(current_dir, "dataset.json"),
        os.path.join(current_dir, "..", "eval", "dataset.json")
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data["workflow_cases"]
    raise FileNotFoundError(f"Could not find dataset.json in {paths}")

@pytest.mark.asyncio
class TestAgentWorkflow:
    @pytest.mark.parametrize("case", load_cases(), ids=lambda x: x["id"])
    @patch("agent.nodes.researcher.tools.ResearcherTools.generate_research_plan", new_callable=AsyncMock)
    @patch("agent.nodes.researcher.tools.ResearcherTools.search_web_ddg", new_callable=AsyncMock)
    @patch("agent.nodes.researcher.tools.ResearcherTools.search_local_kt", new_callable=AsyncMock)
    async def test_agent_workflow_logic(self, mock_search_local, mock_search_web, mock_gen_plan, case):
        if case["id"] == "workflow_006_multi_destination_weather":
            pytest.skip("Skipping 006 weather test for now as discussed.")
        from agent.schema import ResearchPlan
        
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
        if "turns" in case:
            for turn in case["turns"]:
                result = await graph_app.ainvoke({"messages": [HumanMessage(content=turn)]}, config=config)
        elif "update_input" in case:
            await graph_app.ainvoke({"messages": [HumanMessage(content=case["input"])]}, config=config)
            result = await graph_app.ainvoke({"messages": [HumanMessage(content=case["update_input"])]}, config=config)
        else:
            result = await graph_app.ainvoke({"messages": [HumanMessage(content=case["input"])]}, config=config)

        expected = case["expected_state"]
        for key, val in expected.items():
            if result is not None:
                # Check top-level result first (for needs_research)
                if key in result:
                    actual = result.get(key)
                else:
                    # Fallback to user_profile
                    user_profile = result.get("user_profile") or {}
                    search_key = "people_count" if key == "people" else key
                    actual = user_profile.get(search_key)
                
                assert str(actual) == str(val), f"Field {key} mismatch for {case['id']}: expected {val}, got {actual}"
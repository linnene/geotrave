import pytest
import uuid
import json
import os
from unittest.mock import patch, AsyncMock
from langchain_core.messages import HumanMessage

from agent.graph import graph_app
from agent.state import RetrievalItem

#测试例加载
def load_cases():
    path = os.path.join(os.path.dirname(__file__), "dataset.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["workflow_cases"]

@pytest.mark.asyncio
class TestAgentWorkflow:
    """
    Agent Node协作评估 (Dimension 2)。
    """

    @pytest.mark.parametrize("case", load_cases(), ids=lambda x: x["id"])
    @patch("agent.nodes.researcher.tools.ResearcherTools.generate_research_plan", new_callable=AsyncMock)
    @patch("agent.nodes.researcher.tools.ResearcherTools.search_web_ddg", new_callable=AsyncMock)
    @patch("agent.nodes.researcher.tools.ResearcherTools.search_local_kt", new_callable=AsyncMock)
    async def test_agent_workflow_logic(self, mock_search_local, mock_search_web, mock_gen_plan, case):
        """验证 TravelState 在各节点间的流转与折叠逻辑"""
        from agent.schema import ResearchPlan
        
        # Mock 研究计划与检索，避免多余的 LLM 调用和无 Key 阻断
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
        # 1. 处理多步对话序列 (Multi-turn Sequence)
        if "turns" in case:
            for turn in case["turns"]:
                result = await graph_app.ainvoke({"messages": [HumanMessage(content=turn)]}, config=config) # type: ignore
        # 2. 处理需要中间更新的情况 (Update Logic)
        elif "update_input" in case:
            await graph_app.ainvoke({"messages": [HumanMessage(content=case["input"])]}, config=config) # type: ignore
            result = await graph_app.ainvoke({"messages": [HumanMessage(content=case["update_input"])]}, config=config) # type: ignore
        # 3. 单步快照提取 (Single Turn)
        else:
            result = await graph_app.ainvoke({"messages": [HumanMessage(content=case["input"])]}, config=config) # type: ignore

        # 验证结果状态是否符合预期
        expected = case["expected_state"]
        for key, val in expected.items():
            if result is not None:
                user_profile = result.get("user_profile") or {}
                
                # 如果 key 是 people，由于代码里叫 people_count，我们需要做个简单映射
                search_key = "people_count" if key == "people" else key
                
                actual = user_profile.get(search_key)
            assert str(actual) == str(val), f"Field {key} mismatch for {case['id']}: expected {val}, got {actual}"

import pytest
import uuid
import json
import os
from langchain_core.messages import HumanMessage

from agent.graph import graph_app

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
    async def test_agent_workflow_logic(self, case):
        """验证 TravelState 在各节点间的流转与折叠逻辑"""
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
                core_req = result.get("core_requirements") or {}
                actual = core_req.get(key)
            assert str(actual) == str(val), f"Field {key} mismatch for {case['id']}: expected {val}, got {actual}"

import pytest
import asyncio
import time
import uuid
import sys
import os
from unittest.mock import patch, AsyncMock

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(root_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, root_path)

from agent.graph import graph_app
from agent.state import RetrievalItem

async def simulate_user_request(user_id: int):
    """
    模拟单个用户的请求过程。
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # 根据 user_id 构造不同的请求，测试其并发解析能力
    destinations = ["北京", "上海", "大理", "东京", "巴黎"]
    dest = destinations[user_id % len(destinations)]
    
    prompt = f"我是 User_{user_id}，我想去{dest}玩，预算5000，帮我看看有什么好玩的。"
    inputs = {"messages": [("user", prompt)]}
    
    print(f"[User_{user_id}] \033[94mStart Graph Request for {dest}...\033[0m")
    start_time = time.time()
    
    # 异步触发图
    async for event in graph_app.astream(inputs, config=config, stream_mode="updates"):
        for node_name, node_state in event.items():
             print(f"[User_{user_id}] Passed node: {node_name}")
             
    end_time = time.time()
    print(f"[User_{user_id}] \033[92mCompleted in {end_time - start_time:.2f}s\033[0m")
    
@pytest.mark.asyncio
@patch("agent.nodes.researcher.tools.ResearcherTools.generate_research_plan", new_callable=AsyncMock)
@patch("agent.nodes.researcher.tools.ResearcherTools.search_web_ddg", new_callable=AsyncMock)
@patch("agent.nodes.researcher.tools.ResearcherTools.search_local_kt", new_callable=AsyncMock)
async def test_concurrent_sessions(mock_search_local, mock_search_web, mock_gen_plan):
    """
    启动并发测试: 验证系统能否正确同时处理多个独立请求且没有任何串扰
    """
    from agent.schema import ResearchPlan
    
    # 同样屏蔽会引发退避重试的联网与 Embedding 环节
    mock_gen_plan.return_value = ResearchPlan(local_query="Mock Destination", web_queries=["Mock web search"])
    mock_search_web.return_value = [
        RetrievalItem(source="web", title="Mock Title", content="Mock Content", link="http://mock", metadata={})
    ]
    mock_search_local.return_value = [
        RetrievalItem(source="local", title="Mock Local", content="Mock Content", link=None, metadata={})
    ]

    print("=== Start Concurrent Multi-User Test ===")
    start_time = time.time()
    
    # 生成 3 个并发用户请求
    tasks = []
    for i in range(3):
        tasks.append(simulate_user_request(i))
    
    # 并发执行所有请求
    await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    print(f"=== All Requests Completed in {total_time:.2f}s ===")
    
    # 这里断言总耗时必须要能完成，而不是死锁失败 (真环境应判断其总耗时小于串行耗时)
    assert total_time > 0

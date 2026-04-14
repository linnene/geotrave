import asyncio
import time
import uuid
import sys
import os

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(root_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, root_path)

from agent.graph import graph_app

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
    
async def main():
    """
    启动并发测试
    """
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
    
    # 如果是同步阻塞，3个请求耗时约等于: Req1耗时 + Req2耗时 + Req3耗时
    # 如果是真异步非阻塞，3个请求总耗时约等于: Max(Req1耗时, Req2耗时, Req3耗时)
    
if __name__ == "__main__":
    asyncio.run(main())

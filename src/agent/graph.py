"""
Module: src.agent.graph
Responsibility: Defines the StateGraph topology for GeoTrave Agent 2.0.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from src.database.checkpointer import SqliteCheckpointer
import src.agent.state.state as state_mod

# Factory function to get or create the app
# Use a dictionary to store loop-specific app instances to avoid "Lock bound to different loop" errors
_apps = {}

async def get_travel_app():
    """
    Async factory to initialize the graph with an async checkpointer.
    """
    global _apps
    import asyncio
    current_loop = asyncio.get_running_loop()
    
    # Check for closed loops in cache
    _apps = {loop: app for loop, app in _apps.items() if not loop.is_closed()}
    
    if current_loop not in _apps:
        # 1. Initialize Graph with state schema
        workflow = StateGraph(state_mod.TravelState)

        # 2. Register Nodes
        from src.agent.nodes.gateway.node import gateway_node
        from src.agent.nodes.analyst.node import analyst_node
        from src.agent.nodes.reply.node import reply_node
        from src.agent.nodes.manager.node import manager_node
        from src.agent.nodes.research.subgraph import research_loop_subgraph
        from src.agent.nodes.recommender.node import recommender_node
        from src.agent.nodes.planner.node import planner_node

        workflow.add_node("gateway", gateway_node)
        workflow.add_node("analyst", analyst_node)
        workflow.add_node("reply", reply_node)
        workflow.add_node("manager", manager_node)
        workflow.add_node("research_loop", research_loop_subgraph)
        workflow.add_node("recommender", recommender_node)
        workflow.add_node("planner", planner_node)

        # 3. Define Edges
        workflow.set_entry_point("gateway")

        # Gateway Routing: 不安全内容直达 reply，安全内容固定进入 analyst
        def gateway_router(state: state_mod.TravelState) -> str:
            signs = state.get("execution_signs")
            if signs and not signs.is_safe:
                return "reply"
            return "analyst"

        workflow.add_conditional_edges(
            "gateway",
            gateway_router,
            {
                "analyst": "analyst",
                "reply": "reply"
            }
        )

        # Manager Routing: Post-analyst 路由，Manager 不再负责 analyst 的分发
        def manager_router(state: state_mod.TravelState) -> str:
            route = state.get("route_metadata")
            target = route.next_node if route else "reply"

            mapping = {
                "research_loop": "research_loop",
                "recommender": "recommender",
                "planner": "planner",
                "reply": "reply"
            }
            return mapping.get(target, "reply")

        workflow.add_conditional_edges(
            "manager",
            manager_router,
            {
                "reply": "reply",
                "research_loop": "research_loop",
                "recommender": "recommender",
                "planner": "planner",
            }
        )

        # Analyst → Manager: 需求提取完成后交给 Manager 做后续路由
        workflow.add_edge("analyst", "manager")
        # research_loop 子图闭环完成后回到 Manager 进行下一跳决策
        workflow.add_edge("research_loop", "manager")
        # Recommender 完成后 → Reply 呈现结果给用户，等待下一轮输入
        workflow.add_edge("recommender", "reply")
        # Planner 完成后返回给前端（呈现最终行程）
        workflow.add_edge("planner", END)

        # After replying, wait for next user input
        workflow.add_edge("reply", END)

        # 4. Persistence
        # Initialize checkpointer
        checkpointer = await SqliteCheckpointer.get_instance()
        
        # Attach serializer (register all state Pydantic models used in TravelState)
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                ('src.agent.state.schema', 'RouteMetadata'),
                ('src.agent.state.schema', 'UserProfile'),
                ('src.agent.state.schema', 'TraceLog'),
                ('src.agent.state.schema', 'ResearchManifest'),
                ('src.agent.state.schema', 'ExecutionSigns'),
                ('src.agent.state.schema', 'SearchTask'),
                ('src.agent.state.schema', 'ResearchLoopInternal'),
                ('src.agent.state.schema', 'ResearchResult'),
                ('src.agent.state.schema', 'CriticResult'),
                ('src.agent.state.schema', 'LoopSummary'),
                ('src.agent.state.schema', 'RecommendationItem'),
                ('src.agent.state.schema', 'RecommenderOutput'),
                ('src.agent.state.schema', 'Activity'),
                ('src.agent.state.schema', 'DayPlan'),
                ('src.agent.state.schema', 'PlannerOutput'),
                ('src.agent.state.schema', 'UserSelections'),
            ]
        )
        checkpointer.serde = serializer
        
        # Compile with checkpointer
        _apps[current_loop] = workflow.compile(checkpointer=checkpointer)
    return _apps[current_loop]

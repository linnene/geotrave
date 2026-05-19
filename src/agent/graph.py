"""
Module: src.agent.graph
Responsibility: Defines the StateGraph topology for GeoTrave Agent 2.0.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Send
from src.database.checkpointer import SqliteCheckpointer
from src.utils.logger import get_logger
import src.agent.state.state as state_mod

_router_logger = get_logger("GraphRouter")

# Factory function to get or create the app
# Use a dictionary to store loop-specific app instances to avoid "Lock bound to different loop" errors
_apps = {}

async def get_travel_app():
    """
    Async factory to initialize the graph with an async checkpointer.
    """
    global _apps
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
        from src.agent.nodes.research.dimension_planner.node import dimension_planner_node
        from src.agent.nodes.research.merge.node import research_merge_node
        from src.agent.nodes.recommender.node import recommender_node
        from src.agent.nodes.planner.node import planner_node

        workflow.add_node("gateway", gateway_node)
        workflow.add_node("analyst", analyst_node)
        workflow.add_node("reply", reply_node)
        workflow.add_node("manager", manager_node)
        workflow.add_node("research_loop", research_loop_subgraph)
        workflow.add_node("dimension_planner", dimension_planner_node)
        workflow.add_node("research_merge", research_merge_node)
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

        # Manager Routing: research_loop 现在映射到 dimension_planner
        def manager_router(state: state_mod.TravelState) -> str:
            route = state.get("route_metadata")
            target = route.next_node if route else "reply"

            mapping = {
                "research_loop": "dimension_planner",
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
                "dimension_planner": "dimension_planner",
                "recommender": "recommender",
                "planner": "planner",
            }
        )

        # DimensionPlanner fan-out: 根据 planned_dimensions 扇出并行 research_loop
        def dimension_fanout(state: state_mod.TravelState):
            dims = state.get("planned_dimensions", [])
            if not dims:
                _router_logger.info("DimensionFanout: no dimensions → research_merge directly")
                return "research_merge"
            _router_logger.info("DimensionFanout: fanning out %d parallel branches: %s", len(dims), dims)
            dim_hints = state.get("dimension_hints", {})
            parent_messages = state.get("messages", [])
            return [
                Send("research_loop", {
                    "focus_dimension": dim,
                    "dimension_hints": {dim: dim_hints.get(dim, "")},
                    "messages": parent_messages[-3:] if parent_messages else [],
                    "user_profile": state.get("user_profile"),
                })
                for dim in dims
            ]

        workflow.add_conditional_edges(
            "dimension_planner",
            dimension_fanout,
            {
                "research_loop": "research_loop",
                "research_merge": "research_merge",
            }
        )

        # Research Loop exit routing: 并行模式时先汇聚到 research_merge
        def research_exit_router(state: state_mod.TravelState) -> str:
            focus = state.get("focus_dimension")
            target = "research_merge" if focus else "manager"
            _router_logger.info(
                "ResearchExit: branch [%s] completed → routing to %s",
                focus or "none", target,
            )
            return target
    
        workflow.add_conditional_edges(
            "research_loop",
            research_exit_router,
            {
                "research_merge": "research_merge",
                "manager": "manager",
            }
        )

        # Analyst → Manager: 需求提取完成后交给 Manager 做后续路由
        workflow.add_edge("analyst", "manager")
        # research_merge → Manager: 并行结果汇聚后回到 Manager
        workflow.add_edge("research_merge", "manager")
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
                ('src.agent.state.schema.control', 'RouteMetadata'),
                ('src.agent.state.schema.control', 'ExecutionSigns'),
                ('src.agent.state.schema.control', 'TraceLog'),
                ('src.agent.state.schema.domain', 'UserProfile'),
                ('src.agent.state.schema.domain', 'SearchTask'),
                ('src.agent.state.schema.domain', 'RetrievalMetadata'),
                ('src.agent.state.schema.research', 'ResearchManifest'),
                ('src.agent.state.schema.research', 'ResearchLoopInternal'),
                ('src.agent.state.schema.research', 'ResearchResult'),
                ('src.agent.state.schema.research', 'CriticResult'),
                ('src.agent.state.schema.research', 'LoopSummary'),
                ('src.agent.state.schema.llm_contracts', 'DimensionItem'),
                ('src.agent.state.schema.llm_contracts', 'DimensionPlannerOutput'),
                ('src.agent.state.schema.delivery', 'RecommendationItem'),
                ('src.agent.state.schema.delivery', 'RecommenderOutput'),
                ('src.agent.state.schema.delivery', 'Activity'),
                ('src.agent.state.schema.delivery', 'DayPlan'),
                ('src.agent.state.schema.delivery', 'PlannerOutput'),
            ]
        )
        checkpointer.serde = serializer
        
        # Compile with checkpointer
        _apps[current_loop] = workflow.compile(checkpointer=checkpointer)
    return _apps[current_loop]

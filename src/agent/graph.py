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
_app = None

async def get_travel_app():
    """
    Async factory to initialize the graph with an async checkpointer.
    """
    global _app
    if _app is None:
        # 1. Initialize Graph with state schema
        workflow = StateGraph(state_mod.TravelState)

        # 2. Register Nodes
        from src.agent.nodes.gateway.node import gateway_node
        from src.agent.nodes.analyst.node import analyst_node
        from src.agent.nodes.reply.node import reply_node
        from src.agent.nodes.manager.node import manager_node
        from src.agent.nodes.query_generator.node import query_generator_node
        workflow.add_node("gateway", gateway_node)
        workflow.add_node("analyst", analyst_node)
        workflow.add_node("reply", reply_node)
        workflow.add_node("manager", manager_node)
        workflow.add_node("query_generator", query_generator_node) 

        # 3. Define Edges
        workflow.set_entry_point("gateway")

        # Gateway Routing: 仅根据 execution_signs 判断去向
        def gateway_router(state: state_mod.TravelState) -> str:
            signs = state.get("execution_signs")
            if signs and not signs.is_safe:
                return "reply"
            # 正常放行通过 (根据架构图，Gateway流向应为Reply或Manager)
            return "manager"

        workflow.add_conditional_edges(
            "gateway",
            gateway_router,
            {
                "manager": "manager",
                "reply": "reply"
            }
        )

        # Manager Routing: Manager决策路由
        def manager_router(state: state_mod.TravelState) -> str:
            route = state.get("route_metadata")
            target = route.next_node if route else "reply"
            
            # 建立映射表防止节点未注册
            mapping = {
                "query_generator": "query_generator", # 临时映射
                "recommender": "reply", # 临时映射
                
                "planner": "reply", # 临时映射
                "analyst": "analyst",
                "reply": "reply"
            }
            return mapping.get(target, "reply")

        workflow.add_conditional_edges(
            "manager",
            manager_router,
            {
                "analyst": "analyst",
                "reply": "reply",
                "query_generator": "query_generator"
            }
        )

        # Analyst flow: 始终回到 Manager，由全局大脑决定下一步
        workflow.add_edge("analyst", "manager")
        workflow.add_edge("query_generator", "manager")

        # After replying, wait for next user input
        workflow.add_edge("reply", END)

        # 4. Persistence
        # Initialize checkpointer
        checkpointer = await SqliteCheckpointer.get_instance()
        
        # Cleanup default session on startup to ensure a fresh state
        try:
            await SqliteCheckpointer.delete_checkpoint("session1")
        except Exception as e:
            from src.utils.logger import get_logger
            get_logger("Graph").warning(f"Failed to cleanup default session: {e}")

        # Attach serializer
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                ('src.agent.state.sc·hema', 'RouteMetadata'),
                ('src.agent.state.schema', 'UserProfile'),
                ('src.agent.state.schema', 'TraceLog'),
                ('src.agent.state.schema', 'ResearchManifest'),
                ('src.agent.state.schema', 'ExecutionSigns')
            ]
        )
        checkpointer.serde = serializer
        
        # Compile with checkpointer
        _app = workflow.compile(checkpointer=checkpointer)
    return _app

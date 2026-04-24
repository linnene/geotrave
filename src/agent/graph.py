"""
Module: src.agent.graph
Responsibility: Defines the StateGraph topology for GeoTrave Agent 2.0.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import src.agent.state.state as state_mod

def create_travel_graph():
    """
    Initializes and compiles the LangGraph state machine.
    Workflow: Gateway -> Analyst -> Manager -> ...
    """
    # 1. Initialize Graph with state schema
    workflow = StateGraph(state_mod.TravelState)

    # 2. Register Nodes
    from src.agent.nodes.gateway.node import gateway_node
    from src.agent.nodes.analyst.node import analyst_node
    from src.agent.nodes.reply.node import reply_node
    from src.agent.nodes.manager.node import manager_node
    workflow.add_node("gateway", gateway_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("reply", reply_node)
    workflow.add_node("manager", manager_node)

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
            "query_generator": "reply", # 临时映射
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
            "reply": "reply"
        }
    )

    # Analyst flow: 始终回到 Manager，由全局大脑决定下一步
    workflow.add_edge("analyst", "manager")

    # After replying, wait for next user input
    workflow.add_edge("reply", END)

    # 4. Persistence
    # Define a serializer with explicit allowlist to prevent "unregistered type" warnings
    # In latest LangGraph, this is passed directly into the checkpointer's constructor.
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ('src.agent.state.schema', 'RouteMetadata'),
            ('src.agent.state.schema', 'UserProfile'),
            ('src.agent.state.schema', 'TraceLog'),
            ('src.agent.state.schema', 'ResearchManifest'),
            ('src.agent.state.schema', 'ExecutionSigns')
        ]
    )
    
    checkpointer = MemorySaver(serde=serializer)
    
    return workflow.compile(checkpointer=checkpointer)

# Direct instance for import
travel_app = create_travel_graph()

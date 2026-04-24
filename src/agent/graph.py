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
    workflow.add_node("gateway", gateway_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("reply", reply_node)

    # 3. Define Edges
    workflow.set_entry_point("gateway")

    # Gateway Routing: 仅根据 execution_signs 判断去向
    def gateway_router(state: state_mod.TravelState) -> str:
        signs = state.get("execution_signs")
        if signs and not signs.is_safe:
            return "reply"
        # 正常放行通过 (根据架构图，Gateway流向应为Reply或Manager，目前Manager映射到Analyst)
        return "manager"

    workflow.add_conditional_edges(
        "gateway",
        gateway_router,
        {
            "manager": "analyst",
            "reply": "reply"
        }
    )

    # Analyst flow: 根据需求完整性决定
    def analyst_router(state: state_mod.TravelState) -> list[str]:
        # 目前简单实现，始终回复用户
        return ["reply"]

    workflow.add_conditional_edges(
        "analyst",
        analyst_router,
        {
            "reply": "reply"
        }
    )

    # Reply flow
    # After replying, we wait for next user input, so it flows to END
    workflow.add_edge("reply", END)

    # 4. Persistence
    # Define a serializer with explicit allowlist to prevent "unregistered type" warnings
    # In latest LangGraph, this is passed directly into the checkpointer's constructor.
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ('src.agent.state.schema', 'RouteMetadata'),
            ('src.agent.state.schema', 'UserProfile'),
            ('src.agent.state.schema', 'TraceLog'),
            ('src.agent.state.schema', 'ResearchManifest')
        ]
    )
    
    checkpointer = MemorySaver(serde=serializer)
    
    return workflow.compile(checkpointer=checkpointer)

# Direct instance for import
travel_app = create_travel_graph()

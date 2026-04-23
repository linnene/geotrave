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
    workflow.set_entry_point("gateway")

    # Gateway Routing
    workflow.add_conditional_edges(
        "gateway",
        lambda state: state["route_metadata"].next_node,
        {
            "manager": "analyst", # Gateway typically flows to Analyst for parsing
            "reply": "reply",
            "__end__": END
        }
    )

    # Analyst flow: ALWAYS wake up reply, optionally end the current turn's exploration
    def analyst_router(state: state_mod.TravelState) -> list[str]:
        route = state.get("route_metadata")
        if not route:
            return ["reply"]
        
        # We always want to reply to the user. 
        # If core info is met, we might trigger other logic in the future,
        # but for now, we just flow to reply and let it end.
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

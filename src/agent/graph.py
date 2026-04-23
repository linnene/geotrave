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

    # Gateway Routing
    workflow.add_conditional_edges(
        "gateway",
        lambda state: state["route_metadata"].next_node,
        {
            "manager": "analyst", # Temporary mapping: Gateway -> Analyst (Manager logic logic placeholder)
            "reply": "reply",
            "__end__": END
        }
    )

    # Analyst flow
    workflow.add_conditional_edges(
        "analyst",
        lambda state: state["route_metadata"].next_node,
        {
            "manager": END, # Manager placeholder
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

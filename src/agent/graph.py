"""
Module: src.agent.graph
Responsibility: Defines the StateGraph topology for GeoTrave Agent 2.0.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from src.agent.state.state import TravelState
from src.agent.nodes.gateway.node import gateway_node

def create_travel_graph():
    """
    Initializes and compiles the LangGraph state machine.
    Workflow: Gateway -> Manager -> ...
    """
    # 1. Initialize Graph with state schema
    workflow = StateGraph(TravelState)

    # 2. Register Nodes
    workflow.add_node("gateway", gateway_node)

    # 3. Define Edges (Gateway as entry point)
    workflow.set_entry_point("gateway")

    # Gateway Routing: Decision based on route_metadata (set by node)
    # Note: Manager node will be added in subsequent steps
    workflow.add_conditional_edges(
        "gateway",
        lambda state: state["route_metadata"].next_node
    )

    return workflow.compile()

# Direct instance for import
travel_app = create_travel_graph()

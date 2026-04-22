"""
Module: src.agent.graph
Responsibility: Defines the StateGraph topology for GeoTrave Agent 2.0.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from src.agent.state.state import TravelState
from src.agent.nodes.gateway.node import gateway_node
from src.agent.nodes.analyst.node import analyst_node

def create_travel_graph():
    """
    Initializes and compiles the LangGraph state machine.
    Workflow: Gateway -> Analyst -> Manager -> ...
    """
    # 1. Initialize Graph with state schema
    workflow = StateGraph(TravelState)

    # 2. Register Nodes
    workflow.add_node("gateway", gateway_node)
    workflow.add_node("analyst", analyst_node)

    # 3. Define Edges
    workflow.set_entry_point("gateway")

    # Gateway Routing
    workflow.add_conditional_edges(
        "gateway",
        lambda state: state["route_metadata"].next_node,
        {
            "manager": "analyst", # Temporary mapping: Gateway -> Analyst (Manager logic logic placeholder)
            "__end__": END
        }
    )

    # Analyst flow (Analyst usually flows back to Manager for next step decision)
    # For now, we point to END as Manager is not implemented.
    workflow.add_edge("analyst", END)

    return workflow.compile()

# Direct instance for import
travel_app = create_travel_graph()

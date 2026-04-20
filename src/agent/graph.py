"""
Module: src.agent.graph
Responsibility: Defines the LangGraph state machine, nodes, and conditional edges for the travel agent.
Parent Module: src.agent
Dependencies: langgraph, src.agent.state, src.agent.nodes, src.agent.rules

Refactoring Standard: Strict absolute imports, explicit workflow definitions, and clean compilation.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agent.state import TravelState
from src.agent.nodes.router.router import router_node
from src.agent.nodes.analyzer.analyzer import analyzer_node
from src.agent.nodes.researcher.researcher import researcher_node
from src.agent.rules import route_after_analyzer, route_after_router

# ========== workflow ==========
workflow = StateGraph(TravelState)

# 1. Register nodes
workflow.add_node("router", router_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("researcher", researcher_node)

# 2. Define edge structure
# Every interaction begins with the security/intent gateway (Router)
workflow.add_edge(START, "router")

# Post-router logic: Dispatch based on classified intent
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "analyzer": "analyzer",
        "researcher": "researcher",
        END: END
    }
)

# Post-analyzer logic: Determine if research is needed or if questions persist
workflow.add_conditional_edges(
    "analyzer",
    route_after_analyzer,
    {
        "researcher": "researcher",
        END: END
    }
)

# Implementation remains straightforward for retrieval
workflow.add_edge("researcher", END)

# Initializing in-memory checkpointer 
# Persistent memory is handled at the state layer; this manages ephemeral graph checkpoints.
memory = MemorySaver()

# Compile the final application
graph_app = workflow.compile(checkpointer=memory)

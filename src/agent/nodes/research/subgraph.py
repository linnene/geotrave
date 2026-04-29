"""
Module: src.agent.nodes.research.subgraph
Responsibility: Assembles the Research Loop subgraph
                (QG → Search → Critic ⇄ QG | Hash → END).
Parent Module: src.agent.nodes.research
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from src.agent.state.state import TravelState
from .query_generator.node import query_generator_node
from .search.node import search_node
from .critic.node import critic_node
from .hash.node import hash_node


def _critic_router(state: TravelState) -> str:
    research_data = state.get("research_data")

    loop_state = research_data.loop_state if research_data else None
    
    if loop_state and loop_state.continue_loop:
        return "query_generator"
    return "hash"


def build_research_loop_subgraph() -> CompiledStateGraph:
    subgraph = StateGraph(TravelState)

    subgraph.add_node("query_generator", query_generator_node)
    subgraph.add_node("search", search_node)
    subgraph.add_node("critic", critic_node)
    subgraph.add_node("hash", hash_node)

    subgraph.set_entry_point("query_generator")

    subgraph.add_edge("query_generator", "search")
    subgraph.add_edge("search", "critic")

    subgraph.add_conditional_edges(
        "critic",
        _critic_router,
        {"query_generator": "query_generator", "hash": "hash"},
    )

    subgraph.add_edge("hash", END)

    return subgraph.compile()


research_loop_subgraph = build_research_loop_subgraph()

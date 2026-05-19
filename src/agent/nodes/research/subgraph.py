"""
Module: src.agent.nodes.research.subgraph
Responsibility: Assembles the Research Loop subgraph
                (QG → Search → Critic ⇄ QG | Hash → END).
Parent Module: src.agent.nodes.research
Dependencies: langgraph, src.agent.state, src.agent.nodes
"""

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from src.agent.state.schema.research_loop_state import ResearchLoopState
from src.utils.logger import get_logger
from .query_generator.node import query_generator_node
from .search.node import search_node
from .critic.node import critic_node
from .hash.node import hash_node

_router_logger = get_logger("CriticRouter")


def _critic_router(state: ResearchLoopState) -> str:
    research_data = state.get("research_data")
    loop_state = research_data.loop_state if research_data else None

    if loop_state and loop_state.continue_loop:
        _router_logger.info(
            "CriticRouter → QG (loop_iter=%d, passed=%d/%d)",
            loop_state.loop_iteration,
            len(loop_state.all_passed_results),
            len(loop_state.query_results),
        )
        return "query_generator"
    _router_logger.info(
        "CriticRouter → Hash (loop_iter=%d, passed=%d)",
        loop_state.loop_iteration if loop_state else -1,
        len(loop_state.all_passed_results) if loop_state else 0,
    )
    return "hash"


def build_research_loop_subgraph() -> CompiledStateGraph:
    subgraph = StateGraph(ResearchLoopState)

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

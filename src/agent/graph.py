from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import TravelState
from agent.nodes.analyzer import analyzer_node
from agent.nodes.researcher import researcher_node
from agent.router import route_after_analyzer

# ========== workflow ==========
workflow = StateGraph(TravelState)

# signal nodes
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("researcher", researcher_node)

# edges
workflow.add_edge(START, "analyzer")

workflow.add_conditional_edges(
    "analyzer",
    route_after_analyzer,
    {
        "researcher": "researcher",
        END: END
    }
)

# TODO:添加其他节点和边
workflow.add_edge("researcher", END)

# Initializing in-memory checkpointer
memory = MemorySaver()

# compile graph
graph_app = workflow.compile(checkpointer=memory)

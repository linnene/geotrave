from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import TravelState
from agent.nodes.router.router import router_node
from agent.nodes.analyzer.analyzer import analyzer_node
from agent.nodes.researcher.researcher import researcher_node
from agent.rules import route_after_analyzer, route_after_router

# ========== workflow ==========
workflow = StateGraph(TravelState)

# signal nodes
workflow.add_node("router", router_node)
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("researcher", researcher_node)

# edges
# 每次用户发起对话都从 router 进行安全性、意图的前置扫描
workflow.add_edge(START, "router")

# router 出来之后通过边缘判断函数决定前往分析还是拦截甚至跳过
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "analyzer": "analyzer",
        "researcher": "researcher",
        END: END
    }
)

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

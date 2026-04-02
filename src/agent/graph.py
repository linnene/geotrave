from langgraph.graph import StateGraph, START, END

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

# 增加条件边：根据分析结果选择下一步
workflow.add_conditional_edges(
    "analyzer",
    route_after_analyzer,
    {
        "researcher": "researcher",
        END: END
    }
)

# 检索完后暂时先结束（等规划师节点好了再接规划师）
workflow.add_edge("researcher", END)

# compile graph
graph_app = workflow.compile()

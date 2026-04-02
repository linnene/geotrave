from langgraph.graph import StateGraph, START, END

from src.agent.state import TravelState
from src.agent.nodes.analyzer import analyzer_node

# ========== 编排工作流 ==========
workflow = StateGraph(TravelState)

# 1. 注册节点 (员工)
workflow.add_node("analyzer", analyzer_node)

# 2. 画图连线 (流程)
workflow.add_edge(START, "analyzer")
workflow.add_edge("analyzer", END)

# 3. 编译发布
graph_app = workflow.compile()
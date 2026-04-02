from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langgraph.graph import StateGraph, MessagesState, START, END

from utils.config import (
    OPENAI_API_KEY, 
    MODEL_BASE_URL, 
    MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    TIMEOUT
)

llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=SecretStr(OPENAI_API_KEY), 
    base_url=MODEL_BASE_URL, 
    
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=TIMEOUT,                  
    disable_streaming=True,
)


# 2. 定义节点逻辑：直接调用 LLM
async def call_model(state: MessagesState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}

# 3. 编排图逻辑
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

# 4. 编译并导出给 FastAPI 使用
graph_app = workflow.compile()
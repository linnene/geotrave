from fastapi import APIRouter
from .schema import ChatRequest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from typing import Any, Dict
from agent.graph import graph_app

router = APIRouter(tags=["Chat"])

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):

    # 构建 LangGraph 输入状态
    input_state: Dict[str, Any] = {"messages": [HumanMessage(content=request.message)]}
    
    # 调用模型 (LangGraph graph_app)
    # 使用 request 中的 session_id 作为 thread_id 维护状态
    config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}
    result = await graph_app.ainvoke(input_state, config=config) # type: ignore
    
    # 获取模型最后一条回复（防御性处理空消息列表）
    messages = result.get("messages", [])
    last_message = messages[-1] if messages else None
    
    return {
        "reply": last_message.content if last_message is not None else "",
        "session_id": request.session_id,
        "status": "success"
    }
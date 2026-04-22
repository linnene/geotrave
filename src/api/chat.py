"""
Module: src.api.chat
Responsibility: Endpoint for interacting with the LangGraph-based AI agent.
Parent Module: src.api
Dependencies: fastapi, langchain_core, src.api.schema, src.agent.graph
"""

from typing import Any, Dict, cast
from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.api.schema import ChatRequest
from src.agent.graph import travel_app
from src.agent.state.state import TravelState
from src.utils import logger

router = APIRouter()

@router.post("/")
async def chat_endpoint(request: ChatRequest):
    """
    Standard chat interface that processes messages via the GeoTrave StateGraph.
    Delegates state retrieval to LangGraph persistence via thread_id.
    """
    logger.info(f"[Chat API] Received message for session: {request.session_id}")
    
    # Construct minimal input state (Delta).
    # LangGraph will merge this with existing state in Checkpointer using thread_id.
    # Casting to TravelState to satisfy Pylance while only providing the message update.
    input_state = cast(TravelState, {
        "messages": [HumanMessage(content=request.message)]
    })
    
    # Configure the persistent thread for LangGraph memory
    run_config: RunnableConfig = {
        "configurable": {"thread_id": request.session_id}
    }
    
    try:
        # Invoke the compiled graph asynchronously.
        # Graph retrieves historical user_profile, research_data etc. automatically.
        result = await travel_app.ainvoke(input_state, config=run_config)
        
        # Extract the final AI response from the message history
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        
        return {
            "reply": last_message.content if last_message is not None else "对不起，我无法生成回复。",
            "session_id": request.session_id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"[Chat API] Agent invocation failed: {e}")
        return {
            "reply": f"代理执行出错: {str(e)}",
            "session_id": request.session_id,
            "status": "error"
        }

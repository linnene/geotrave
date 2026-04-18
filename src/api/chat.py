"""
Chat API Module: Exposes agents endpoints for user interaction.

Handles routing requests to the LangGraph application and maintaining session state.

Parent Module: src.api
Dependencies: fastapi, agent.graph, api.schema
"""

from typing import Any, Dict
from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from api.schema import ChatRequest, ChatResponse
from agent.graph import graph_app
from utils.logger import logger

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main dialogue endpoint.
    
    Invokes the GeoTrave agent graph and returns the processed AI response.
    """
    logger.info(f"[Chat API] Received message for session: {request.session_id}")
    
    # Construct LangGraph input state
    input_state: Dict[str, Any] = {
        "messages": [HumanMessage(content=request.message)]
    }
    
    # Configure thread-based persistence for cross-request history
    config: RunnableConfig = {
        "configurable": {"thread_id": request.session_id}
    }
    
    try:
        # Invoke the graph (async)
        result = await graph_app.ainvoke(input_state, config=config)
        
        # Extract the final message content with safety checks
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        reply_content = last_message.content if last_message else "Internal Error: No response generated."
        
        return ChatResponse(
            reply=reply_content,
            session_id=request.session_id,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"[Chat API] Graph execution error: {str(e)}")
        return ChatResponse(
            reply="I encountered an error while processing your request. Please try again later.",
            session_id=request.session_id,
            status="error"
        )

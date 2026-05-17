"""
Module: src.api.chat
Responsibility: Endpoint for interacting with the LangGraph-based AI agent.
Parent Module: src.api
Dependencies: fastapi, langchain_core, src.api.schema, src.agent.graph
"""

from typing import cast
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.api.schema import ChatRequest, ChatResponse
from src.agent.graph import get_travel_app
from src.agent.state.state import TravelState
from src.utils import logger

router = APIRouter()


def _serializable(obj):
    """Convert Pydantic model to dict, pass through None/lists unchanged."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serializable(item) for item in obj]
    return obj


@router.post("")
@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Standard chat interface that processes messages via the GeoTrave StateGraph.
    Delegates state retrieval to LangGraph persistence via thread_id.
    """
    logger.info("[Chat API] Received message for session: %s", request.session_id)

    travel_app = await get_travel_app()

    input_state = cast(TravelState, {
        "messages": [HumanMessage(content=request.message)]
    })

    run_config: RunnableConfig = {
        "configurable": {"thread_id": request.session_id}
    }

    try:
        result = await travel_app.ainvoke(input_state, config=run_config)

        plan_data = result.get("plan_data")
        if plan_data is not None:
            reply_text = "行程已生成，请查看下方规划详情。"
        else:
            messages = result.get("messages", [])
            last_message = messages[-1] if messages else None
            reply_text = (
                last_message.content if last_message is not None
                else "对不起，我无法生成回复。"
            )

        response = ChatResponse(
            reply=reply_text,
            session_id=request.session_id,
            status="success",
            route=_serializable(result.get("route_metadata")),
            signs=_serializable(result.get("execution_signs")),
            trace=_serializable(result.get("trace_history")),
            profile=_serializable(result.get("user_profile")),
            recommendation=result.get("recommendation_data"),
            plan=plan_data,
        )

        # Upsert session metadata (non-blocking on failure)
        try:
            from src.database.session_store import SqliteSessionStore
            store = await SqliteSessionStore.get_instance()
            await store.upsert_on_success(
                session_id=request.session_id,
                user_message=request.message,
            )
        except Exception as e:
            logger.warning("[Chat API] Session metadata upsert failed: %s", e)

        return response
    except Exception as e:
        logger.error("[Chat API] Agent invocation failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "reply": "系统处理请求时发生内部错误，请稍后重试。",
                "session_id": request.session_id,
                "status": "error",
            },
        )

"""
Test Suite: Chat API
Mapping: /src/api/chat.py
Priority: P0 — Agent response contract
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage
from src.agent.state.schema import (
    RouteMetadata, ExecutionSigns, TraceLog, UserProfile,
    PlannerOutput, DayPlan,
)


# =============================================================================
# P0 — Response fields
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_chat_returns_new_fields():
    """chat_endpoint returns route, signs, trace, profile in response."""
    from src.api.chat import chat_endpoint
    from src.api.schema import ChatRequest

    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(return_value={
        "messages": [AIMessage(content="Test reply")],
        "route_metadata": RouteMetadata(next_node="reply", reason="info"),
        "execution_signs": ExecutionSigns(is_safe=True),
        "trace_history": [TraceLog(node="gateway", status="SUCCESS", latency_ms=10)],
        "user_profile": UserProfile(destination=["Paris"]),
        "recommendation_data": None,
        "plan_data": None,
    })

    with (
        patch("src.api.chat.get_travel_app", AsyncMock(return_value=mock_app)),
        patch("src.database.session_store.SqliteSessionStore.get_instance", AsyncMock()),
    ):
        response = await chat_endpoint(ChatRequest(message="Hello"))

    assert response.status == "success"
    assert response.route["next_node"] == "reply"
    assert response.signs["is_safe"] is True
    assert len(response.trace) == 1
    assert response.trace[0]["node"] == "gateway"
    assert response.profile["destination"] == ["Paris"]
    assert response.reply == "Test reply"


# =============================================================================
# P0 — Planner path
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_planner_path_returns_explicit_reply():
    """When plan_data is set, reply is explicit text not stale message."""
    from src.api.chat import chat_endpoint
    from src.api.schema import ChatRequest

    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(return_value={
        "messages": [],
        "route_metadata": None,
        "execution_signs": None,
        "trace_history": [],
        "user_profile": None,
        "recommendation_data": None,
        "plan_data": PlannerOutput(days=[]),
    })

    with (
        patch("src.api.chat.get_travel_app", AsyncMock(return_value=mock_app)),
        patch("src.database.session_store.SqliteSessionStore.get_instance", AsyncMock()),
    ):
        response = await chat_endpoint(ChatRequest(message="计划行程"))

    assert response.status == "success"
    assert response.plan is not None
    assert response.reply == "行程已生成，请查看下方规划详情。"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_non_planner_uses_ai_message():
    """Without plan_data, reply comes from messages[-1]."""
    from src.api.chat import chat_endpoint
    from src.api.schema import ChatRequest

    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(return_value={
        "messages": [AIMessage(content="请告诉我更多需求")],
        "route_metadata": None,
        "execution_signs": None,
        "trace_history": [],
        "user_profile": None,
        "recommendation_data": None,
        "plan_data": None,
    })

    with (
        patch("src.api.chat.get_travel_app", AsyncMock(return_value=mock_app)),
        patch("src.database.session_store.SqliteSessionStore.get_instance", AsyncMock()),
    ):
        response = await chat_endpoint(ChatRequest(message="Hi"))

    assert response.reply == "请告诉我更多需求"


# =============================================================================
# P1 — Error path
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_chat_error_path():
    """Agent failure returns 500 with error status."""
    from src.api.chat import chat_endpoint
    from src.api.schema import ChatRequest

    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(side_effect=RuntimeError("Boom"))

    with (
        patch("src.api.chat.get_travel_app", AsyncMock(return_value=mock_app)),
        patch("src.database.session_store.SqliteSessionStore.get_instance", AsyncMock()),
    ):
        from fastapi.responses import JSONResponse
        response = await chat_endpoint(ChatRequest(message="X"))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
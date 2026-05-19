"""
Test Suite: Graph Compilation
Mapping: /src/agent/graph.py
Priority: P0 — Full graph topology verification to catch regressions before deploy
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langgraph.checkpoint.memory import InMemorySaver


# =============================================================================
# Helpers
# =============================================================================

def _make_checkpointer():
    """Return an InMemorySaver suitable for graph compilation tests."""
    return InMemorySaver()


async def _compile_graph():
    """Compile and return the app, patching the real checkpointer."""
    checkpointer = _make_checkpointer()
    mock_get = AsyncMock(return_value=checkpointer)
    with patch(
        "src.agent.graph.SqliteCheckpointer.get_instance",
        new=mock_get,
    ):
        from src.agent.graph import get_travel_app
        app = await get_travel_app()
    return app, mock_get


# =============================================================================
# P0 — graph compilation and topology verification
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_graph_compiles_successfully():
    """get_travel_app() compiles without error → returns CompiledStateGraph."""
    app, mock_get = await _compile_graph()
    assert app is not None
    assert hasattr(app, "get_graph")
    mock_get.assert_awaited_once()


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_all_9_nodes_registered():
    """All 9 top-level nodes are registered in the compiled graph."""
    app, _ = await _compile_graph()
    graph = app.get_graph()
    node_names = set(graph.nodes.keys()) - {"__start__", "__end__"}

    expected = {
        "gateway", "analyst", "reply", "manager",
        "dimension_planner", "research_loop", "research_merge",
        "recommender", "planner",
    }
    assert node_names == expected


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_is_entry_point():
    """Graph edge from __start__ → gateway confirms entry point."""
    app, _ = await _compile_graph()
    graph = app.get_graph()
    start_edges = [e for e in graph.edges if e.source == "__start__"]
    assert len(start_edges) == 1
    assert start_edges[0].target == "gateway"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_gateway_router_paths():
    """gateway conditional edges must define analyst and reply targets."""
    app, _ = await _compile_graph()
    graph = app.get_graph()
    gateway_targets = {e.target for e in graph.edges if e.source == "gateway"}

    assert "analyst" in gateway_targets
    assert "reply" in gateway_targets


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_manager_router_targets():
    """manager conditional edges must route to all 4 targets."""
    app, _ = await _compile_graph()
    graph = app.get_graph()
    manager_targets = {e.target for e in graph.edges if e.source == "manager"}

    assert manager_targets == {"reply", "dimension_planner", "recommender", "planner"}


# =============================================================================
# P1 — serializer and checkpointer integration
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_serializer_registered_with_checkpointer():
    """JsonPlusSerializer is attached to checkpointer.serde."""
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    checkpointer = _make_checkpointer()
    mock_get = AsyncMock(return_value=checkpointer)

    with patch(
        "src.agent.graph.SqliteCheckpointer.get_instance",
        new=mock_get,
    ):
        from src.agent.graph import get_travel_app
        await get_travel_app()

    assert checkpointer.serde is not None
    assert isinstance(checkpointer.serde, JsonPlusSerializer)


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_graph_caches_per_loop():
    """Second call with same loop returns cached instance."""
    checkpointer = _make_checkpointer()
    mock_get = AsyncMock(return_value=checkpointer)

    with patch(
        "src.agent.graph.SqliteCheckpointer.get_instance",
        new=mock_get,
    ):
        from src.agent.graph import get_travel_app
        app1 = await get_travel_app()
        app2 = await get_travel_app()

    assert app1 is app2
    assert mock_get.await_count == 1

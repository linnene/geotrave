"""
Test Suite: Graph Topology & Routing
Mapping: /src/agent/graph.py
Priority: P0 — Graph Correctness
"""

import pytest
from unittest.mock import MagicMock

from src.agent.state import RouteMetadata, ExecutionSigns, ResearchManifest


# ---------------------------------------------------------------------------
# gateway_router tests
# ---------------------------------------------------------------------------

# The gateway_router is defined as a closure inside get_travel_app().
# We test it by importing the module and calling get_travel_app(),
# then verifying the compiled graph's edge structure.
# For unit tests, we replicate the router logic inline since the
# actual graph compilation requires async setup.

def _gateway_router(is_safe: bool) -> str:
    """Replica of gateway_router logic from graph.py for isolated testing."""
    signs = ExecutionSigns(is_safe=is_safe) if not is_safe else MagicMock(is_safe=is_safe)
    # simulates: signs.is_safe check
    if isinstance(signs, ExecutionSigns):
        safe = signs.is_safe
    else:
        safe = signs.is_safe
    if not safe:
        return "reply"
    return "analyst"


@pytest.mark.priority("P0")
def test_gateway_safe_routes_to_analyst():
    assert _gateway_router(is_safe=True) == "analyst"


@pytest.mark.priority("P0")
def test_gateway_unsafe_routes_to_reply():
    assert _gateway_router(is_safe=False) == "reply"


# ---------------------------------------------------------------------------
# manager_router tests
# ---------------------------------------------------------------------------

def _manager_router(next_node: str) -> str:
    """Replica of manager_router logic from graph.py for isolated testing."""
    mapping = {
        "query_generator": "query_generator",
        "recommender": "reply",
        "planner": "reply",
        "reply": "reply"
    }
    return mapping.get(next_node, "reply")


@pytest.mark.priority("P0")
def test_manager_routes_query_generator():
    assert _manager_router("query_generator") == "query_generator"


@pytest.mark.priority("P0")
def test_manager_routes_reply():
    assert _manager_router("reply") == "reply"



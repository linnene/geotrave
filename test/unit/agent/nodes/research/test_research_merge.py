"""
Test Suite: ResearchMerge Node
Mapping: /src/agent/nodes/research/merge/node.py
Priority: P0 — Phase 7 aggregation node for parallel research branches
"""

import pytest

from src.agent.state import ExecutionSigns, ResearchManifest
from src.agent.state.schema import CriticResult, ResearchLoopInternal


# =============================================================================
# P0 — research_merge_node core logic
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_research_merge_clears_dimension_fields():
    """planned_dimensions cleared, focus_dimension set to None."""
    from src.agent.nodes.research.merge.node import research_merge_node

    manifest = ResearchManifest()
    state = {
        "planned_dimensions": ["food", "attraction"],
        "focus_dimension": "food",
        "research_data": manifest,
    }

    result = await research_merge_node(state)

    assert result["planned_dimensions"] == []
    assert result["focus_dimension"] is None


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_research_merge_writes_trace():
    """Trace history written with SUCCESS status."""
    from src.agent.nodes.research.merge.node import research_merge_node

    manifest = ResearchManifest()
    state = {
        "planned_dimensions": ["attraction"],
        "focus_dimension": None,
        "research_data": manifest,
    }

    result = await research_merge_node(state)

    assert len(result["trace_history"]) == 1
    assert result["trace_history"][0].node == "research_merge"
    assert result["trace_history"][0].status == "SUCCESS"
    assert "dimensions_merged" in result["trace_history"][0].detail


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_research_merge_counts_hashes():
    """research_hashes are correctly counted in trace detail."""
    from src.agent.nodes.research.merge.node import research_merge_node

    manifest = ResearchManifest(
        research_hashes={
            "query1": ["hash_a", "hash_b"],
            "query2": ["hash_c"],
        }
    )
    state = {
        "planned_dimensions": ["a", "b"],
        "focus_dimension": None,
        "research_data": manifest,
    }

    result = await research_merge_node(state)

    assert result["trace_history"][0].detail["total_hashes"] == 3


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_research_merge_empty_research_data():
    """No research_data → hashes_count = 0, no crash."""
    from src.agent.nodes.research.merge.node import research_merge_node

    state = {
        "planned_dimensions": [],
        "focus_dimension": None,
        "research_data": None,
    }

    result = await research_merge_node(state)

    assert result["trace_history"][0].detail["total_hashes"] == 0
    assert result["planned_dimensions"] == []
    assert result["focus_dimension"] is None


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_research_merge_dims_in_trace():
    """Trace detail includes dimensions_merged list."""
    from src.agent.nodes.research.merge.node import research_merge_node

    manifest = ResearchManifest()
    state = {
        "planned_dimensions": ["food", "attraction", "accommodation"],
        "focus_dimension": None,
        "research_data": manifest,
    }

    result = await research_merge_node(state)

    assert result["trace_history"][0].detail["dimensions_merged"] == ["food", "attraction", "accommodation"]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_research_merge_preserves_execution_signs():
    """execution_signs are read for diagnostics but not modified."""
    from src.agent.nodes.research.merge.node import research_merge_node

    manifest = ResearchManifest()
    state = {
        "planned_dimensions": ["attraction"],
        "focus_dimension": None,
        "research_data": manifest,
        "execution_signs": ExecutionSigns(research_rounds=2, is_core_complete=True),
    }

    result = await research_merge_node(state)

    # merge_node does not touch execution_signs in its return dict
    assert "execution_signs" not in result

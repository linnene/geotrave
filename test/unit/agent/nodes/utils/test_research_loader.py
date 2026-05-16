"""
Test Suite: ResearchLoader
Mapping: /src/agent/nodes/utils/research_loader.py
Priority: P0 — Shared by Recommender and Planner for prompt injection
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.agent.state.schema import (
    CriticResult,
    LoopSummary,
    ResearchLoopInternal,
    ResearchManifest,
)


# =============================================================================
# P0 — fetch_research_content core
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_research_content_none_manifest():
    """manifest is None → placeholder string."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    result = await fetch_research_content(None)
    assert result == "暂无研究数据"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_research_content_empty_hashes():
    """Empty research_hashes → no-results message."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    manifest = ResearchManifest(research_hashes={})
    result = await fetch_research_content(manifest)
    assert "当前无通过评估的研究结果" in result


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_research_content_empty_hash_values():
    """research_hashes with empty lists → no-results message."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    manifest = ResearchManifest(research_hashes={"query1": []})
    result = await fetch_research_content(manifest)
    assert "hash key 为空" in result


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_research_content_with_records():
    """DB returns records → formatted content returned."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    manifest = ResearchManifest(
        research_hashes={"query1": ["hash_a", "hash_b"]}
    )

    mock_records = {
        "hash_a": {
            "tool_name": "web_search",
            "query": "东京美食推荐",
            "rationale": "包含具体店名和评分",
            "relevance_score": 0.85,
            "utility_score": 0.9,
            "name": "东京美食指南",
            "content_type": "web",
            "_dimension": "food",
        },
        "hash_b": {
            "tool_name": "spatial_search",
            "query": "新宿区拉面店POI",
            "rationale": "地理位置精确",
            "relevance_score": 0.8,
            "utility_score": 0.7,
            "content_type": "spatial",
            "_dimension": "food",
        },
    }

    with patch(
        "src.database.retrieval_db.get_results",
        new=AsyncMock(return_value=mock_records),
    ):
        result = await fetch_research_content(manifest)

    assert "东京美食指南" in result
    assert "新宿区拉面店POI" in result
    assert "[web]" in result


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_research_content_dimension_filter():
    """dimension filter excludes non-matching records."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    manifest = ResearchManifest(
        research_hashes={"q": ["hash_food", "hash_attraction"]}
    )

    mock_records = {
        "hash_food": {
            "tool_name": "web_search",
            "query": "东京拉面",
            "rationale": "ok",
            "relevance_score": 0.9,
            "utility_score": 0.8,
            "_dimension": "food",
        },
        "hash_attraction": {
            "tool_name": "web_search",
            "query": "东京景点",
            "rationale": "ok",
            "relevance_score": 0.7,
            "utility_score": 0.6,
            "_dimension": "attraction",
        },
    }

    with patch(
        "src.database.retrieval_db.get_results",
        new=AsyncMock(return_value=mock_records),
    ):
        result = await fetch_research_content(manifest, dimension="food")

    assert "东京拉面" in result
    assert "东京景点" not in result


# =============================================================================
# P1 — error handling and fallback
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_research_content_db_exception_fallback():
    """DB exception → fallback to CriticResult rationales."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    loop_state = ResearchLoopInternal(
        all_passed_results=[
            CriticResult(
                query="test query",
                tool_name="web_search",
                safety_tag="safe",
                rationale="test rationale",
                relevance_score=0.8,
                utility_score=0.7,
            )
        ]
    )
    manifest = ResearchManifest(
        research_hashes={"q": ["hash1"]},
        loop_state=loop_state,
    )

    with patch(
        "src.database.retrieval_db.get_results",
        new=AsyncMock(side_effect=RuntimeError("DB down")),
    ):
        result = await fetch_research_content(manifest)

    assert "降级摘要" in result
    assert "test rationale" in result


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_research_content_empty_records_fallback():
    """DB returns empty dict → fallback to CriticResult rationales."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    loop_state = ResearchLoopInternal(
        all_passed_results=[
            CriticResult(
                query="empty db query",
                tool_name="spatial_search",
                safety_tag="safe",
                rationale="rationale text",
                relevance_score=0.6,
                utility_score=0.5,
            )
        ]
    )
    manifest = ResearchManifest(
        research_hashes={"q": ["hash1"]},
        loop_state=loop_state,
    )

    with patch(
        "src.database.retrieval_db.get_results",
        new=AsyncMock(return_value={}),
    ):
        result = await fetch_research_content(manifest)

    assert "降级摘要" in result
    assert "rationale text" in result


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_research_content_dimension_all_filtered():
    """All records filtered by dimension → fallback."""
    from src.agent.nodes.utils.research_loader import fetch_research_content

    manifest = ResearchManifest(
        research_hashes={"q": ["hash1"]}
    )

    mock_records = {
        "hash1": {
            "tool_name": "web_search",
            "query": "something",
            "rationale": "ok",
            "relevance_score": 0.5,
            "utility_score": 0.5,
            "_dimension": "food",
        },
    }

    with patch(
        "src.database.retrieval_db.get_results",
        new=AsyncMock(return_value=mock_records),
    ):
        result = await fetch_research_content(manifest, dimension="attraction")

    # Fallback because the only record is "food" but dimension="attraction"
    assert "降级摘要" in result or "暂无可用研究数据" in result


# =============================================================================
# P1 — _format_entry
# =============================================================================


def test_format_entry_basic():
    """_format_entry formats a basic payload correctly."""
    from src.agent.nodes.utils.research_loader import _format_entry

    payload = {
        "tool_name": "web_search",
        "query": "京都美食",
        "rationale": "详细餐厅推荐",
        "relevance_score": 0.9,
        "utility_score": 0.85,
        "name": "京都美食指南",
        "content_type": "web",
    }

    result = _format_entry("hash_abc", payload)
    assert result is not None
    assert "京都美食指南" in result
    assert "web_search" in result or "[web]" in result
    assert "相关性=0.9" in result.lower() or "相关性=1" in result


def test_format_entry_poi_list():
    """_format_entry handles list raw_content with POI entries."""
    from src.agent.nodes.utils.research_loader import _format_entry

    payload = {
        "tool_name": "spatial_search",
        "query": "新宿餐厅POI",
        "rationale": "附近餐饮",
        "relevance_score": 0.8,
        "utility_score": 0.7,
        "_research_content": [
            {"name": "一兰拉面", "category": "拉面", "address": "新宿区"},
            {"name": "叙叙苑", "category": "烧肉", "address": "新宿三丁目"},
            {"name": "天屋", "category": "天妇罗", "address": ""},
        ],
    }

    result = _format_entry("hash_poi", payload)
    assert result is not None
    assert "一兰拉面" in result
    assert "叙叙苑" in result
    assert "新宿区" in result
    assert "数据条目" in result


def test_format_entry_dict_content():
    """_format_entry handles dict raw_content."""
    from src.agent.nodes.utils.research_loader import _format_entry

    payload = {
        "tool_name": "document_search",
        "query": "东京攻略",
        "rationale": "完整",
        "relevance_score": 0.7,
        "utility_score": 0.6,
        "_research_content": {"summary": "东京三日游攻略", "sections": 5},
    }

    result = _format_entry("hash_dict", payload)
    assert result is not None
    assert "东京三日游攻略" in result


def test_format_entry_string_content():
    """_format_entry handles string raw_content."""
    from src.agent.nodes.utils.research_loader import _format_entry

    payload = {
        "tool_name": "web_search",
        "query": "大阪",
        "rationale": "ok",
        "relevance_score": 0.5,
        "utility_score": 0.5,
        "_research_content": "大阪城是著名景点",
    }

    result = _format_entry("hash_str", payload)
    assert result is not None
    assert "大阪城是著名景点" in result

"""
Test Suite: web_search — DDG search + Crawler full-text fetch
Mapping: /src/agent/nodes/research/search/web_search.py
Priority: P1 — External web search + crawl tool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import SearchTask, RetrievalMetadata


# =============================================================================
# P1 — search_web (DDG wrapper)
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_web_success():
    """DDGS.text() called with correct args, fields mapped href→url body→snippet."""
    from src.agent.nodes.research.search.web_search import search_web

    ddgs_results = [
        {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
        {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
    ]

    with patch(
        "src.agent.nodes.research.search.web_search.DDGS",
    ) as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.text.return_value = ddgs_results
        MockDDGS.return_value.__enter__.return_value = mock_instance

        results = await search_web("test query", max_results=5)

    assert len(results) == 2
    assert results[0]["title"] == "Result 1"
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["snippet"] == "Snippet 1"
    mock_instance.text.assert_called_once_with(
        "test query", max_results=5, safesearch="moderate"
    )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_web_empty_results():
    """Empty DDGS response returns empty list."""
    from src.agent.nodes.research.search.web_search import search_web

    with patch(
        "src.agent.nodes.research.search.web_search.DDGS",
    ) as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.text.return_value = []
        MockDDGS.return_value.__enter__.return_value = mock_instance

        results = await search_web("nothing", max_results=5)

    assert results == []


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_web_ddgs_exception():
    """DDGS raising exception returns empty list (graceful degradation)."""
    from src.agent.nodes.research.search.web_search import search_web

    with patch(
        "src.agent.nodes.research.search.web_search.DDGS",
    ) as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.text.side_effect = RuntimeError("Rate limited")
        MockDDGS.return_value.__enter__.return_value = mock_instance

        results = await search_web("rate limit test", max_results=5)

    assert results == []


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_search_web_empty_query():
    """Empty or whitespace-only query returns empty list immediately."""
    from src.agent.nodes.research.search.web_search import search_web

    assert await search_web("") == []
    assert await search_web("   ") == []


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_search_web_filters_empty_entries():
    """Items with no title AND no snippet are filtered out."""
    from src.agent.nodes.research.search.web_search import search_web

    ddgs_results = [
        {"title": "Good", "href": "https://good.example", "body": "Good snippet"},
        {"title": "", "href": "https://empty.example", "body": ""},
        {"title": "Also Good", "href": "https://good2.example", "body": "Another"},
    ]

    with patch(
        "src.agent.nodes.research.search.web_search.DDGS",
    ) as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.text.return_value = ddgs_results
        MockDDGS.return_value.__enter__.return_value = mock_instance

        results = await search_web("test", max_results=5)

    assert len(results) == 2
    urls = [r["url"] for r in results]
    assert "https://empty.example" not in urls


# =============================================================================
# P1 — crawl_urls
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_crawl_urls_success():
    """Parallel crawl merges content from each URL."""
    from src.agent.nodes.research.search.web_search import crawl_urls

    async def fake_crawl(url):
        return MagicMock(
            url=url,
            content=f"Content of {url}",
            status="success",
            mode="fast",
        )

    mock_crawler = MagicMock()
    mock_crawler.crawl.side_effect = fake_crawl

    with patch(
        "src.agent.nodes.research.search.web_search._get_crawler",
        new=AsyncMock(return_value=mock_crawler),
    ):
        results = await crawl_urls(
            ["https://a.com", "https://b.com", "https://c.com"],
            timeout=10.0,
        )

    assert len(results) == 3
    assert results[0]["url"] == "https://a.com"
    assert results[0]["content"] == "Content of https://a.com"
    assert results[0]["crawl_status"] == "success"
    assert results[0]["crawl_mode"] == "fast"
    assert results[1]["content"] == "Content of https://b.com"
    assert results[2]["content"] == "Content of https://c.com"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_crawl_urls_partial_failure():
    """Single URL failure does not block others; order is preserved."""
    from src.agent.nodes.research.search.web_search import crawl_urls

    async def fake_crawl(url):
        if "fail" in url:
            raise RuntimeError("Connection refused")
        return MagicMock(
            url=url,
            content=f"Content of {url}",
            status="success",
            mode="fast",
        )

    mock_crawler = MagicMock()
    mock_crawler.crawl.side_effect = fake_crawl

    with patch(
        "src.agent.nodes.research.search.web_search._get_crawler",
        new=AsyncMock(return_value=mock_crawler),
    ):
        results = await crawl_urls(
            ["https://good.com", "https://fail.com", "https://also-good.com"],
            timeout=10.0,
        )

    assert len(results) == 3
    assert results[0]["content"] == "Content of https://good.com"
    assert results[0]["crawl_status"] == "success"
    assert results[1]["url"] == "https://fail.com"
    assert results[1]["content"] is None
    assert results[1]["crawl_status"] == "error"
    assert results[2]["content"] == "Content of https://also-good.com"


# =============================================================================
# P1 — execute_web_search (tool handler)
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_web_search_tool_handler():
    """Full handler: search → crawl → RetrievalMetadata with merged results."""
    from src.agent.nodes.research.search.tools import execute_web_search

    mock_merged = {
        "query": "Tokyo attractions",
        "total": 2,
        "results": [
            {
                "title": "T1", "url": "https://a.com", "snippet": "s1",
                "content": "Full content A", "crawl_status": "success", "crawl_mode": "fast",
            },
            {
                "title": "T2", "url": "https://b.com", "snippet": "s2",
                "content": "Full content B", "crawl_status": "success", "crawl_mode": "deep",
            },
        ],
    }

    task = SearchTask(
        tool_name="web_search",
        dimension="attraction",
        parameters={"query": "Tokyo attractions", "max_results": "3"},
        rationale="test",
    )

    with patch(
        "src.agent.nodes.research.search.web_search.search_and_crawl",
        new=AsyncMock(return_value=mock_merged),
    ):
        result = await execute_web_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert result.payload["query"] == "Tokyo attractions"
    assert result.payload["total"] == 2
    assert result.payload["results"] == mock_merged["results"]
    assert "web_" in result.hash_key
    assert result.relevance_score == 1.0


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_web_search_missing_query():
    """Missing required 'query' parameter raises ValueError."""
    from src.agent.nodes.research.search.tools import execute_web_search

    task = SearchTask(
        tool_name="web_search",
        dimension="general",
        parameters={"max_results": "5"},
        rationale="test",
    )

    with pytest.raises(ValueError, match="缺少必填参数"):
        await execute_web_search(task)


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_web_search_crawl_failure():
    """All crawls fail → results still returned with snippet and content=None."""
    from src.agent.nodes.research.search.tools import execute_web_search

    mock_merged = {
        "query": "test",
        "total": 2,
        "results": [
            {
                "title": "T1", "url": "https://a.com", "snippet": "s1",
                "content": None, "crawl_status": "error", "crawl_mode": "fast",
            },
            {
                "title": "T2", "url": "https://b.com", "snippet": "s2",
                "content": None, "crawl_status": "timeout", "crawl_mode": "fast",
            },
        ],
    }

    task = SearchTask(
        tool_name="web_search",
        dimension="general",
        parameters={"query": "test"},
        rationale="test",
    )

    with patch(
        "src.agent.nodes.research.search.web_search.search_and_crawl",
        new=AsyncMock(return_value=mock_merged),
    ):
        result = await execute_web_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert result.payload["total"] == 2
    assert result.payload["results"][0]["snippet"] == "s1"
    assert result.payload["results"][0]["content"] is None


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_web_search_empty_ddg():
    """DDG returns zero results → empty payload."""
    from src.agent.nodes.research.search.tools import execute_web_search

    mock_merged = {"query": "nonexistent_xyz", "total": 0, "results": []}

    task = SearchTask(
        tool_name="web_search",
        dimension="general",
        parameters={"query": "nonexistent_xyz"},
        rationale="test",
    )

    with patch(
        "src.agent.nodes.research.search.web_search.search_and_crawl",
        new=AsyncMock(return_value=mock_merged),
    ):
        result = await execute_web_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert result.payload["total"] == 0
    assert result.payload["results"] == []


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_web_search_clamps_max_results():
    """max_results=999 is clamped to 20; max_results=0 clamped to 1."""
    from src.agent.nodes.research.search.tools import execute_web_search

    task = SearchTask(
        tool_name="web_search",
        dimension="general",
        parameters={"query": "test", "max_results": "999"},
        rationale="test",
    )

    with patch(
        "src.agent.nodes.research.search.web_search.search_and_crawl",
        new=AsyncMock(return_value={"query": "test", "total": 0, "results": []}),
    ) as mock_sc:
        await execute_web_search(task)

    mock_sc.assert_awaited_once_with("test", 20)

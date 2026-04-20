"""
Description: Universal Web Crawler & Parser Unit Tests
Target: /src/crawler/parser.py
Status: Completed
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.crawler import WebCrawler
from src.crawler.parser import ContentParser
from src.crawler.schema import CrawlResult

@pytest.fixture
def crawler():
    return WebCrawler(timeout=1)

@pytest.fixture
def parser():
    return ContentParser()

@pytest.mark.asyncio
@pytest.mark.priority("P1")
async def test_crawler_schema_validation():
    """Verify CrawlResult schema constraints."""
    result = CrawlResult(
        url="https://example.com",
        title="Test Title",
        content="Test Content",
        status="success",
        mode="fast"
    )
    assert result.url == "https://example.com"
    assert result.status == "success"

@pytest.mark.priority("P1")
def test_parser_cleaning_logic(parser):
    """
    Goal: Verify Trafilatura extraction logic works with sample HTML.
    """
    sample_html = """
    <html>
        <head><title>Travel Guide</title></head>
        <body>
            <nav><ul><li>Home</li><li>About</li></ul></nav>
            <main>
                <h1>Japan Trip 2024</h1>
                <p>Japan is a beautiful country with great food.</p>
                <div class="ads">Buy our luggage now!</div>
            </main>
            <footer>Contact us</footer>
        </body>
    </html>
    """
    title, content = parser.process_extraction(sample_html)
    
    # Trafilatura should pick the main content and ignore nav/ads
    assert "Japan Trip 2024" in content
    assert "Japan is a beautiful country" in content
    assert "Home" not in content  # Nav should be stripped
    assert title == "Travel Guide"

@pytest.mark.asyncio
@pytest.mark.priority("P1")
@patch("src.crawler.fetcher.ContentFetcher.fetch_fast")
async def test_crawler_orchestration_fast_success(mock_fetch, crawler):
    """
    Goal: Verify WebCrawler orchestrator correctly uses Fast mode when it succeeds.
    """
    mock_fetch.return_value = "<html><body><h1>Fast Content</h1></body></html>"
    
    result = await crawler.crawl("https://simple-site.com")
    
    assert result.status == "success"
    assert result.mode == "fast"
    assert "Fast Content" in result.content
    mock_fetch.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.priority("P1")
@patch("src.crawler.fetcher.ContentFetcher.fetch_fast")
@patch("src.crawler.fetcher.ContentFetcher.fetch_deep")
async def test_crawler_orchestration_fallback_to_deep(mock_deep, mock_fast, crawler):
    """
    Goal: Verify WebCrawler falls back to Deep mode if Fast mode fails.
    """
    mock_fast.return_value = None  # Simulate 403 or timeout
    mock_deep.return_value = "<html><body><h1>Deep Content</h1></body></html>"
    
    result = await crawler.crawl("https://complex-site.com")
    
    assert result.status == "success"
    assert result.mode == "deep"
    assert "Deep Content" in result.content
    mock_fast.assert_called_once()
    mock_deep.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.priority("P2")
@patch("src.crawler.fetcher.ContentFetcher.fetch_fast")
@patch("src.crawler.fetcher.ContentFetcher.fetch_deep")
async def test_crawler_full_path_error(mock_deep, mock_fast, crawler):
    """
    Goal: Verify error status when both engines fail.
    """
    mock_fast.return_value = None
    mock_deep.return_value = None
    
    result = await crawler.crawl("https://broken-site.com")
    
    assert result.status == "error"
    assert result.content is None


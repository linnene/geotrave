"""
Module: src.agent.nodes.research.search.web_search
Responsibility: DDG web search + Crawler full-text fetch orchestration.
Parent Module: src.agent.nodes.research.search
Dependencies: ddgs.DDGS, src.crawler.WebCrawler
"""

import asyncio
import time
from typing import Any, Dict, List

from ddgs import DDGS

from src.crawler import WebCrawler
from src.utils.logger import get_logger

logger = get_logger("WebSearch")

_MAX_CRAWL_CONCURRENCY = 2
_DEFAULT_CRAWL_TIMEOUT = 60.0

_LOCK = asyncio.Lock()
_crawler: WebCrawler | None = None


async def _get_crawler() -> WebCrawler:
    global _crawler
    if _crawler is None:
        async with _LOCK:
            if _crawler is None:
                _crawler = WebCrawler(timeout=20)
                await _crawler.start_browser()
    return _crawler


async def close_crawler() -> None:
    """Close the shared WebCrawler browser. Safe to call multiple times."""
    global _crawler
    if _crawler is not None:
        await _crawler.close_browser()
        _crawler = None


async def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """DDG web search, returns [{title, url, snippet}]. Empty list on error."""
    if not query or not query.strip():
        return []

    def _sync_search() -> List[Dict[str, str]]:
        try:
            with DDGS() as ddgs:
                raw = ddgs.text(query, max_results=max_results, safesearch="moderate")
        except Exception as exc:
            logger.warning("DDGS error: %s", exc)
            return []

        results: List[Dict[str, str]] = []
        for item in raw:
            title = item.get("title", "")
            url = item.get("href", "")
            snippet = item.get("body", "")
            if title or snippet:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results[:max_results]

    return await asyncio.to_thread(_sync_search)


async def crawl_urls(
    urls: List[str],
    timeout: float = _DEFAULT_CRAWL_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Crawl URLs in parallel with concurrency limit.

    Single URL failure does not block others — failed entries keep
    content=None with crawl_status="error".
    """
    if not urls:
        return []

    semaphore = asyncio.Semaphore(_MAX_CRAWL_CONCURRENCY)
    crawler = await _get_crawler()

    async def _crawl_one(url: str) -> Dict[str, Any]:
        async with semaphore:
            try:
                result = await crawler.crawl(url)
                return {
                    "url": url,
                    "content": result.content,
                    "crawl_status": result.status,
                    "crawl_mode": result.mode,
                }
            except Exception as exc:
                logger.warning("Crawl failed for %s: %s", url, exc)
                return {
                    "url": url,
                    "content": None,
                    "crawl_status": "error",
                    "crawl_mode": "fast",
                }

    tasks = [_crawl_one(url) for url in urls]
    done, pending = await asyncio.wait(
        [asyncio.ensure_future(t) for t in tasks],
        timeout=timeout,
    )

    results: List[Dict[str, Any]] = []
    for t in done:
        try:
            results.append(await t)
        except Exception:
            pass
    for t in pending:
        t.cancel()

    # Preserve original URL order
    result_map = {r["url"]: r for r in results}
    return [result_map.get(url, {"url": url, "content": None, "crawl_status": "timeout", "crawl_mode": "fast"}) for url in urls]


async def search_and_crawl(
    query: str,
    max_results: int = 5,
    max_crawl: int = 3,
) -> Dict[str, Any]:
    """Search DDG then crawl top URLs for full content.

    Returns payload dict ready for RetrievalMetadata.payload.
    """
    t0 = time.time()
    search_results = await search_web(query, max_results)

    if not search_results:
        logger.info("web_search: no DDG results for query=%s", query)
        return {"query": query, "total": 0, "results": []}

    urls_to_crawl = [r["url"] for r in search_results[:max_crawl]]
    crawl_results = await crawl_urls(urls_to_crawl)

    merged: List[Dict[str, Any]] = []
    for sr, cr in zip(search_results[:max_crawl], crawl_results):
        merged.append({**sr, **cr})

    elapsed = time.time() - t0
    success = sum(1 for m in merged if m.get("content"))
    logger.info(
        "web_search: query=%s ddg=%d crawled=%d/%d (%.1fs)",
        query, len(search_results), success, len(merged), elapsed,
    )

    return {"query": query, "total": len(merged), "results": merged}

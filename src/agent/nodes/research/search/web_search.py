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

# Browser pool — each instance owns its own Chromium process, enabling true
# parallelism that bypasses crawl4ai's internal asyncio.Lock in arun().
_POOL_SIZE = 3
_pool: asyncio.Queue[WebCrawler] | None = None
_pool_lock = asyncio.Lock()
_pool_instances: List[WebCrawler] = []


async def _get_pool() -> asyncio.Queue[WebCrawler]:
    """Lazily initialise and return the browser pool."""
    global _pool, _pool_instances
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = asyncio.Queue(maxsize=_POOL_SIZE)
                for i in range(_POOL_SIZE):
                    c = WebCrawler(timeout=20)
                    await c.start_browser()
                    _pool.put_nowait(c)
                    _pool_instances.append(c)
                logger.info("Browser pool initialized: %d instances", _POOL_SIZE)
    return _pool


async def close_crawler() -> None:
    """Close all browser instances in the pool. Safe to call multiple times."""
    global _pool, _pool_instances
    if _pool is not None:
        # Drain pool
        while not _pool.empty():
            try:
                _pool.get_nowait()
            except asyncio.QueueEmpty:
                break
        _pool = None
    for c in _pool_instances:
        await c.close_browser()
    _pool_instances.clear()
    logger.info("Browser pool closed")


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
    """Crawl URLs with a browser pool for true parallelism.

    Each concurrent crawl acquires its own browser instance from the pool,
    bypassing crawl4ai's internal asyncio.Lock.  Single URL failure does
    not block others.
    """
    if not urls:
        return []

    pool = await _get_pool()

    async def _crawl_one(url: str) -> Dict[str, Any]:
        crawler = await pool.get()
        try:
            result = await crawler.crawl(url)
            return {
                "url": url,
                "content": result.content,
                "crawl_status": result.status,
                "crawl_mode": result.mode,
                "error_code": result.error_code,
                "error_message": result.error_message,
            }
        except Exception as exc:
            logger.warning("Crawl failed for %s: %s", url, exc)
            return {
                "url": url,
                "content": None,
                "crawl_status": "error",
                "crawl_mode": "fast",
                "error_code": "exception",
                "error_message": str(exc)[:500],
            }
        finally:
            await pool.put(crawler)

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
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass

    # Preserve original URL order
    result_map = {r["url"]: r for r in results}
    timeout_fallback = {"url": "", "content": None, "crawl_status": "timeout", "crawl_mode": "fast", "error_code": "timeout", "error_message": "Crawl timed out"}
    return [result_map.get(url, {**timeout_fallback, "url": url}) for url in urls]


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

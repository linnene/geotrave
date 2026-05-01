from typing import Optional, Dict, Any
from .fetcher import ContentFetcher
from .parser import ContentParser
from .schema import CrawlResult, FetchError

class WebCrawler:
    """
    Orchestrator for the crawling process.
    Coordinates between fetcher, parser, and schema.
    """

    def __init__(self, timeout: int = 20):
        self.fetcher = ContentFetcher(timeout=timeout)
        self.parser = ContentParser()

    async def start_browser(self) -> None:
        """Lazily start the managed Chromium browser (one-off)."""
        await self.fetcher.start_browser()

    async def close_browser(self) -> None:
        """Close the managed Chromium browser."""
        await self.fetcher.close_browser()

    async def crawl(self, url: str, force_deep: bool = False) -> CrawlResult:
        """Entry point that manages the fetch-then-parse workflow.

        Fast fetch first; falls back to deep (Chromium) on failure or
        when anti-bot markers are detected in the fast response.
        """
        html = None
        mode = "fast"
        error_code: Optional[str] = None
        error_message: Optional[str] = None

        # Heuristic: certain domains are known to block fast mode or require JS
        block_prone_domains = ["booking.com", "tripadvisor.com", "ctrip.com", "xiaohongshu.com", "xhslink.com"]
        if any(domain in url.lower() for domain in block_prone_domains):
            force_deep = True

        # ── Fast fetch ──────────────────────────────────────────────
        if not force_deep:
            try:
                html = await self.fetcher.fetch_fast(url)
                # If fast mode returns an obvious bot-block message, discard and retry deep
                if html and ("JavaScript is disabled" in html or "verify you're not a robot" in html):
                    html = None
            except FetchError as e:
                error_code = e.error_code
                error_message = e.message

        # ── Deep fetch (fallback) ───────────────────────────────────
        if not html:
            try:
                html = await self.fetcher.fetch_deep(url)
                mode = "deep"
                error_code = None
                error_message = None
            except FetchError as e:
                error_code = error_code or e.error_code
                error_message = error_message or e.message
                mode = "deep" if force_deep else mode

        # ── No HTML — return structured error ───────────────────────
        if not html:
            return CrawlResult(
                url=url,
                content=None,
                status="error",
                mode=mode,
                error_code=error_code,
                error_message=error_message,
            )

        # ── Parse ───────────────────────────────────────────────────
        title, content = self.parser.process_extraction(html)
        status = "success" if content else "no_content_found"

        return CrawlResult(
            url=url,
            title=title,
            content=content,
            status=status,
            mode=mode,
            error_code=error_code,
            error_message=error_message,
        )

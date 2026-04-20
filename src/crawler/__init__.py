from typing import Optional, Dict, Any
from .fetcher import ContentFetcher
from .parser import ContentParser
from .schema import CrawlResult

class WebCrawler:
    """
    Orchestrator for the crawling process.
    Coordinates between fetcher, parser, and schema.
    """
    
    def __init__(self, timeout: int = 20):
        self.fetcher = ContentFetcher(timeout=timeout)
        self.parser = ContentParser()

    async def crawl(self, url: str, force_deep: bool = False) -> CrawlResult:
        """Entry point that manages the fetch-then-parse workflow."""
        html = None
        mode = "fast"
        
        # Heuristic: certain domains are known to block fast mode or require JS
        block_prone_domains = ["booking.com", "tripadvisor.com", "ctrip.com", "xiaohongshu.com", "xhslink.com"]
        if any(domain in url.lower() for domain in block_prone_domains):
            force_deep = True

        if not force_deep:
            html = await self.fetcher.fetch_fast(url)
            # If fast mode returns an obvious bot-block message, retry with deep mode
            if html and ("JavaScript is disabled" in html or "verify you're not a robot" in html):
                html = None

        if not html:
            html = await self.fetcher.fetch_deep(url)
            mode = "deep"

        if not html:
            return CrawlResult(url=url, content=None, status="error", mode=mode)
            
        title, content = self.parser.process_extraction(html)
        
        status = "success" if content else "no_content_found"
        
        return CrawlResult(
            url=url,
            title=title,
            content=content,
            status=status,
            mode=mode
        )

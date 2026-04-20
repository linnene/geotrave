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
        
        if not force_deep:
            html = await self.fetcher.fetch_fast(url)
            
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

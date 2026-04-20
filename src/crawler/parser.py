import trafilatura
import httpx
import asyncio
from typing import Optional, Dict, Any
from readability import Document
from crawl4ai import AsyncWebCrawler
from src.utils.logger import logger

class WebCrawler:
    """
    Universal Web Content Crawler & Parser.
    Focuses on main content extraction and boilerplate removal.
    Uses Dual-Engine approach:
    1. Fast Mode (httpx + trafilatura)
    2. Deep Mode (Crawl4AI/Playwright) for JS-heavy sites.
    """
    
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_fast(self, url: str) -> Optional[str]:
        """Low-latency fetch for simple static pages."""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(f"Fast fetch failed for {url}, falling back to Deep mode: {str(e)}")
            return None

    async def fetch_deep(self, url: str) -> Optional[str]:
        """Deep fetch using Crawl4AI/Playwright for JS-heavy pages (SPA)."""
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    return result.html
                return None
        except Exception as e:
            logger.error(f"Deep fetch failed for {url}: {str(e)}")
            return None

    def clean_content(self, html: str) -> Optional[str]:
        """
        Multi-stage cleaning:
        Stage 1: Trafilatura (Primary - Precision)
        Stage 2: Readability-lxml (Fallback - Recall)
        """
        # Strategy 1: Trafilatura
        extracted = trafilatura.extract(
            html, 
            output_format='markdown',
            include_links=True,
            include_tables=True
        )
        
        if extracted and len(extracted.strip()) > 200:
            return extracted

        # Strategy 2: Readability Fallback (if Trafilatura yields too little)
        try:
            doc = Document(html)
            summary = doc.summary()
            # Convert readable HTML to basic text/markdown snippet
            # (In production, consider adding html2text here for better formatting)
            return trafilatura.extract(summary, output_format='markdown')
        except:
            return extracted

    async def crawl(self, url: str, force_deep: bool = False) -> Dict[str, Any]:
        """High-level entry point with automatic engine selection."""
        html = None
        
        if not force_deep:
            html = await self.fetch_fast(url)
            
        if not html:
            html = await self.fetch_deep(url)

        if not html:
            return {"url": url, "content": None, "status": "error"}
            
        content = self.clean_content(html)
        return {
            "url": url,
            "content": content,
            "status": "success" if content else "no_content_found",
            "mode": "deep" if force_deep or not html else "fast"
        }

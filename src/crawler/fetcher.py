import httpx
from typing import Optional
from crawl4ai import AsyncWebCrawler
from src.utils.logger import logger

class ContentFetcher:
    """Handles the raw data acquisition from the web."""
    
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
            logger.warning(f"Fast fetch failed for {url}: {str(e)}")
            return None

    async def fetch_deep(self, url: str) -> Optional[str]:
        """Deep fetch using Crawl4AI for JS-heavy pages."""
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    return result.html
                return None
        except Exception as e:
            logger.error(f"Deep fetch failed for {url}: {str(e)}")
            return None

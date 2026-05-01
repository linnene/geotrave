import httpx
from typing import Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from src.utils.logger import logger
from .schema import FetchError


class ContentFetcher:
    """Handles the raw data acquisition from the web.

    Reuses a single AsyncWebCrawler (Chromium) instance across all deep
    fetches. The browser is lazily started on first fetch_deep() call
    and kept alive until close_browser() is called.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._crawler: Optional[AsyncWebCrawler] = None

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
        }

        self._browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            use_managed_browser=True,
            viewport_width=1920,
            viewport_height=1080,
            headers=self.headers,
        )

        # 回收阈值: 爬够 500 页后自动回收浏览器进程（释放泄漏内存）
        self._browser_config.max_pages_before_recycle = 500

        self._run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            process_iframes=True,
            wait_until="domcontentloaded",
            js_code="""
                (async () => {
                    window.scrollTo(0, 500);
                    await new Promise(r => setTimeout(r, 6000));
                    window.scrollTo(0, 0);
                })();
            """,
        )

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def start_browser(self) -> None:
        if self._crawler is not None:
            return
        self._crawler = AsyncWebCrawler(config=self._browser_config)
        await self._crawler.start()
        logger.info("ContentFetcher: browser started (managed Chromium)")

    async def close_browser(self) -> None:
        if self._crawler is None:
            return
        await self._crawler.close()
        self._crawler = None
        logger.info("ContentFetcher: browser closed")

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    async def fetch_fast(self, url: str) -> str:
        """Low-latency fetch for simple static pages.

        Returns HTML string on success.
        Raises FetchError with structured error_code on failure.
        """
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=10,
                follow_redirects=True,
                http2=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException as e:
            raise FetchError("timeout", f"Fast fetch timed out: {url}") from e
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            category = f"http_{code // 100}xx"
            raise FetchError(category, f"HTTP {code} for {url}") from e
        except httpx.ConnectError as e:
            raise FetchError("connection", f"Connection failed for {url}") from e
        except Exception as e:
            raise FetchError("unknown", f"Fast fetch failed for {url}: {str(e)}") from e

    async def fetch_deep(self, url: str) -> str:
        """Deep fetch reusing a persistent Crawl4AI browser instance.

        Returns HTML string on success.
        Raises FetchError with structured error_code on failure (including
        anti-bot detection and empty pages).
        """
        try:
            if self._crawler is None:
                await self.start_browser()

            result = await self._crawler.arun(url=url, config=self._run_config)

            if result is None:
                raise FetchError("unknown", "Crawl4AI returned None")

            if not result.success:
                error_msg = getattr(result, "error_message", "") or "unknown error"
                raise FetchError("crawl_failed", str(error_msg)[:500])

            html = result.html
            if not html:
                raise FetchError("empty_or_short", f"No HTML content from {url}")

            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="replace")

            # Anti-bot / challenge detection — fail hard, do not return captcha pages
            forbidden_markers = [
                "verify you're not a robot",
                "JavaScript is disabled",
                "Please enable JavaScript",
                "checking your browser",
                "Access Denied",
                "Attention Required! | Cloudflare",
            ]
            html_lower = html.lower()
            for marker in forbidden_markers:
                if marker.lower() in html_lower:
                    raise FetchError("blocked", f"Anti-bot/challenge page detected for {url} (marker: {marker})")

            if len(html) <= 500:
                raise FetchError("empty_or_short", f"HTML too short ({len(html)} chars) for {url}")

            return html

        except FetchError:
            raise
        except Exception as e:
            raise FetchError("unknown", f"Deep fetch failed for {url}: {str(e)}") from e

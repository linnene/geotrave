"""
Demo: DDG 搜索 + Crawl4AI 全文抓取 + Markdown 转换 — 端到端测试

独立脚本，不依赖 src/ 内部模块，直接测试底层技术栈：
  ddgs → DuckDuckGo 搜索
  crawl4ai.AsyncWebCrawler → 浏览器全文抓取
  trafilatura → HTML → Markdown 清洗
  readability-lxml → 回退提取

用法:
  uv run python script/demo_crawler.py "北海道 旅游 攻略"
  uv run python script/demo_crawler.py "京都 红叶 最佳观赏时间" --max 3
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Windows ProactorEventLoop 修复（Playwright 需要）
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import trafilatura
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from ddgs import DDGS
from readability import Document

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
OUTPUT_DIR = "script/output"
_DEFAULT_QUERY = "北海道 7天 自由行 攻略"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}")


# ---------------------------------------------------------------------------
# Step 1: DDG 搜索
# ---------------------------------------------------------------------------
def search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo 搜索，返回 [{title, url, snippet}]。"""
    _log(f"DDG 搜索: '{query}' (max={max_results})")

    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results, safesearch="moderate"))
    except Exception as exc:
        _log(f"  DDG 搜索失败: {exc}")
        return []

    results = []
    for item in raw:
        title = item.get("title", "")
        url = item.get("href", "")
        snippet = item.get("body", "")
        if title or snippet:
            results.append({"title": title, "url": url, "snippet": snippet})

    _log(f"  DDG 返回 {len(results)} 条结果")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r['title'][:80]}")
        print(f"      URL: {r['url'][:100]}")
        print(f"      {r['snippet'][:120]}...")
    print()
    return results


# ---------------------------------------------------------------------------
# Step 2: Crawl4AI 全文抓取
# ---------------------------------------------------------------------------
async def crawl_urls(
    urls: list[str],
    titles: list[str],
    crawl_timeout: float = 30.0,
) -> list[dict]:
    """用 AsyncWebCrawler 抓取 URL 列表，返回 [{title, url, html, markdown, error}]。"""
    if not urls:
        return []

    _log(f"Crawl4AI: 启动浏览器，抓取 {len(urls)} 个 URL")

    browser_config = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        use_managed_browser=(sys.platform == "win32"),  # Windows 用本机 Chrome 反爬，Linux 用 Playwright
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        process_iframes=False,
        wait_until="domcontentloaded",  # domcontentloaded 而非 networkidle，避免广告/追踪脚本导致永不等
        js_code="""(async () => {
            window.scrollTo(0, 500);
            await new Promise(r => setTimeout(r, 4000));
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, 1000));
        })();""",
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 逐个抓取（crawl4ai 内部有 asyncio.Lock 做串行保护）
        results = []
        for i, (url, title) in enumerate(zip(urls, titles)):
            t0 = time.time()
            _log(f"  抓取 [{i+1}/{len(urls)}]: {title[:60]}...")
            try:
                result = await asyncio.wait_for(
                    crawler.arun(url=url, config=run_config),
                    timeout=crawl_timeout,
                )
                elapsed = time.time() - t0

                if result and result.success and result.html:
                    html = result.html if isinstance(result.html, str) else result.html.decode("utf-8", errors="replace")
                    _log(f"    成功 ({len(html)} 字节, {elapsed:.1f}s)")
                    results.append({"title": title, "url": url, "html": html, "error": None})
                elif result and not result.success:
                    _log(f"    失败: {result.error_message[:100]}")
                    results.append({"title": title, "url": url, "html": None, "error": result.error_message})
                else:
                    _log(f"    无 HTML 内容")
                    results.append({"title": title, "url": url, "html": None, "error": "empty response"})
            except asyncio.TimeoutError:
                _log(f"    超时 ({crawl_timeout}s)")
                results.append({"title": title, "url": url, "html": None, "error": "timeout"})
            except Exception as exc:
                _log(f"    异常: {exc}")
                results.append({"title": title, "url": url, "html": None, "error": str(exc)})

    _log(f"Crawl4AI: 完成，{sum(1 for r in results if r['html'])}/{len(results)} 成功")
    print()
    return results


# ---------------------------------------------------------------------------
# Step 3: HTML → Markdown 清洗
# ---------------------------------------------------------------------------
def html_to_markdown(html: str, fallback_title: str = "") -> tuple[str | None, str | None]:
    """Trafilatura 主提取 + readability-lxml 回退。

    Returns:
        (title, markdown_content)
    """
    # Primary: trafilatura
    md = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=True,
        include_tables=True,
    )

    if md and len(md.strip()) >= 300:
        doc = Document(html)
        return doc.title(), md

    # Fallback: readability-lxml → trafilatura
    try:
        doc = Document(html)
        title = doc.title()
        summary = doc.summary()
        if summary:
            md = trafilatura.extract(summary, output_format="markdown")
            if md and len(md.strip()) >= 100:
                return title, md
    except Exception:
        pass

    # 最后兜底: 返回原始 trafilatura 结果（即使短）
    doc = Document(html)
    return doc.title() or fallback_title, md


# ---------------------------------------------------------------------------
# 汇总与保存
# ---------------------------------------------------------------------------
def save_and_summarize(
    query: str,
    search_results: list[dict],
    crawl_results: list[dict],
) -> None:
    """保存 Markdown 文件到 output 目录，并打印终端摘要。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c if c.isalnum() or c in " _-" else "_" for c in query)[:40]
    filename = os.path.join(OUTPUT_DIR, f"demo_{safe_query}_{ts}.md")

    lines = [
        f"# DDG + Crawl4AI Demo: {query}",
        f"",
        f"**时间**: {datetime.now().isoformat()}",
        f"**DDG 结果数**: {len(search_results)}",
        f"**成功抓取**: {sum(1 for c in crawl_results if c['html'])}/{len(crawl_results)}",
        f"",
        "---",
        f"",
        "## 搜索快照",
        f"",
    ]

    for i, sr in enumerate(search_results):
        lines.append(f"- **[{i+1}] {sr['title']}**")
        lines.append(f"  - URL: {sr['url']}")
        lines.append(f"  - Snippet: {sr['snippet']}")
        lines.append("")

    lines.extend(["---", "", "## 正文提取", ""])

    success_count = 0
    for i, cr in enumerate(crawl_results):
        lines.append(f"### [{i+1}] {cr['title']}")
        lines.append(f"**URL**: {cr['url']}")
        lines.append("")

        if cr["html"]:
            title, md = html_to_markdown(cr["html"], cr["title"])
            if md:
                success_count += 1
                display_title = title or cr["title"]
                lines.append(f"**提取标题**: {display_title}")
                lines.append(f"**Markdown 长度**: {len(md)} 字符")
                lines.append("")
                # 截断预览
                preview = md[:600]
                if len(md) > 600:
                    preview += "...\n\n*(内容已截断，完整版见文件)*"
                lines.append(preview)
                # 完整内容
                lines.append("")
                lines.append("---")
                lines.append("")
                lines.append(f"<!-- FULL_CONTENT_START [{i+1}] -->")
                lines.append("")
                lines.append(md)
                lines.append("")
                lines.append(f"<!-- FULL_CONTENT_END [{i+1}] -->")
            else:
                lines.append("> Markdown 提取失败（内容为空或过短）")
        else:
            lines.append(f"> 抓取失败: {cr.get('error', 'unknown')}")
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    # 终端摘要
    print("=" * 60)
    print("  端到端测试结果")
    print("=" * 60)
    print(f"  搜索词:   {query}")
    print(f"  DDG 结果: {len(search_results)}")
    print(f"  抓取成功: {sum(1 for c in crawl_results if c['html'])}/{len(crawl_results)}")
    print(f"  MD 提取:  {success_count}")
    print(f"  输出文件: {os.path.abspath(filename)}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(query: str, max_results: int, max_crawl: int) -> None:
    print()
    print("╔" + "═" * 58 + "╗")
    print("║  DDG + Crawl4AI → Markdown  端到端测试                     ║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Step 1: DDG 搜索
    search_results = search_ddg(query, max_results)

    if not search_results:
        _log("无搜索结果，退出")
        return

    # Step 2: 抓取前 N 条
    urls = [r["url"] for r in search_results[:max_crawl]]
    titles = [r["title"] for r in search_results[:max_crawl]]
    crawl_results = await crawl_urls(urls, titles)

    # Step 3: 汇总 & 保存
    save_and_summarize(query, search_results, crawl_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DDG 搜索 + Crawl4AI 全文抓取 + Markdown 转换 端到端测试"
    )
    parser.add_argument("query", nargs="?", default=_DEFAULT_QUERY, help="搜索关键词")
    parser.add_argument("--max", type=int, default=5, help="DDG 最大搜索结果数 (默认 5)")
    parser.add_argument("--crawl", type=int, default=3, help="抓取前 N 条 URL (默认 3)")
    args = parser.parse_args()

    asyncio.run(main(args.query, args.max, args.crawl))

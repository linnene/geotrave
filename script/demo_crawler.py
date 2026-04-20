import asyncio
import sys
import os
from src.crawler import WebCrawler

async def run_demo(url: str):
    print(f"\n[GeoTrave Crawler] Starting extraction for: {url}")
    print("-" * 50)
    
    crawler = WebCrawler(timeout=30)
    
    # Run the crawl
    result = await crawler.crawl(url)
    
    if result.status == "success":
        print(f"STATUS: {result.status.upper()}")
        print(f"MODE:   {result.mode.upper()}")
        print(f"TITLE:  {result.title}")
        print("-" * 50)
        print("CONTENT PREVIEW (Cleaned Markdown):")
        
        # Output to terminal
        content = result.content or "No content found"
        print(content[:1000] + ("..." if len(content) > 1000 else ""))
        
        # Save to a temporary file for viewing
        filename = "crawler_output_preview.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {result.title}\n\nURL: {result.url}\n\n---\n\n{result.content}")
        
        print("-" * 50)
        print(f"FULL CONTENT SAVED TO: {os.path.abspath(filename)}")
    else:
        print(f"ERROR: Extraction failed with status '{result.status}'")

if __name__ == "__main__":
    # Use a default travel-related URL if none provided
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://en.wikipedia.org/wiki/Travel"
    asyncio.run(run_demo(test_url))

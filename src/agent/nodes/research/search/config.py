"""
Module: src.agent.nodes.research.search.config
Responsibility: Search node constants — browser pool, crawl concurrency, and timeout parameters.
"""

# Browser pool — each instance owns its own Chromium process
POOL_SIZE = 3

# Maximum concurrent crawl tasks
MAX_CRAWL_CONCURRENCY = 2

# Default crawl timeout in seconds
DEFAULT_CRAWL_TIMEOUT = 60.0

"""
Module: src.agent.nodes.research.search.config
Responsibility: Search node constants — browser pool, crawl concurrency, and timeout parameters.
"""

# Browser pool — each instance owns its own Chromium process
POOL_SIZE = 8

# Maximum concurrent crawl tasks
MAX_CRAWL_CONCURRENCY = 4

# Default crawl timeout in seconds (reduced from 60 — pages >20s are useless for travel)
DEFAULT_CRAWL_TIMEOUT = 20.0

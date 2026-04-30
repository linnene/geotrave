"""
Module: src.main
Responsibility: Application entry point for the GeoTrave Backend API.
Parent Module: src
Dependencies: fastapi, uvicorn, src.api.routes, src.utils

Refactoring Standard: Absolute imports, clear lifespan management, and standardized startup logging.
"""

import fastapi
import uvicorn
import asyncio
import sys
from contextlib import asynccontextmanager

from src.api.routes import router as api_router
from src.database.postgis import close_pool, get_pool
from src.database.retrieval_db import init_retrieval_db
from src.utils import logger

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """
    Manages the startup and shutdown lifecycle of the FastAPI application.
    """
    # Fix ProactorEventLoop issue for Playwright on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("[GeoTrave] Applied WindowsProactorEventLoopPolicy for async subprocess support")

    logger.info("======================================================")
    logger.info(" API Server: Initializing Infrastructure")
    logger.info("======================================================")

    # 初始化 PostGIS 连接池
    await get_pool()
    logger.info("[GeoTrave] PostGIS connection pool initialized")

    # 初始化 Retrieval DB 表 (Research Loop 结果缓存)
    await init_retrieval_db()
    logger.info("[GeoTrave] Retrieval DB table initialized")

    # 构建 BM25 文档索引 (从 PostgreSQL 加载系统文档)
    from src.agent.nodes.research.search.docs import get_document_manager
    doc_mgr = await get_document_manager(await get_pool())
    logger.info(f"[GeoTrave] BM25 document index loaded ({doc_mgr.doc_count()} documents)")

    yield
    # 关闭 Crawler 浏览器实例
    from src.agent.nodes.research.search.web_search import close_crawler
    await close_crawler()
    logger.info("[GeoTrave] WebSearch crawler browser closed")

    await close_pool()
    logger.info("[GeoTrave] API Server shutting down...")
    
# Initialize FastAPI application
app = fastapi.FastAPI(
    title="GeoTrave AI Agent API",
    description="Backend API for travel planning and context-aware research.",
    version="1.0.0",
    lifespan=lifespan
)

# Register API routes using the unified router
app.include_router(api_router)

if __name__ == "__main__":
    # Launch application using uvicorn
    # In production, these should be handled via environment variables or CLI arguments
    uvicorn.run(app, host="0.0.0.0", port=8000)


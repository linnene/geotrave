"""
Module: src.main
Responsibility: Application entry point for the GeoTrave Backend API.
Parent Module: src
Dependencies: fastapi, uvicorn, src.api.routes, src.utils

Refactoring Standard: Absolute imports, clear lifespan management, and standardized startup logging.
"""

import fastapi
import uvicorn
from contextlib import asynccontextmanager

from src.api.routes import router as api_router
from src.utils import logger

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """
    Manages the startup and shutdown lifecycle of the FastAPI application.
    """
    logger.info("======================================================")
    logger.info(" API Server: Initializing Infrastructure")
    logger.info("======================================================")
    yield
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


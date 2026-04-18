"""
GeoTrave FastAPI Entry Point.

This file serves as the main entry point for the GeoTrave API server.
It initializes the FastAPI application, registers API routes, and manages 
the server lifecycle.

Parent Module: src
Dependencies: fastapi, uvicorn, api.routes, utils.logger
"""

import fastapi
import uvicorn
from api.routes import router as api_router
from utils.logger import logger
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """Manage application lifecycle."""
    logger.info("[GeoTrave] FastAPI Server starting...")
    yield
    logger.info("[GeoTrave] FastAPI Server shutting down...")


# Initialize FastAPI application
app = fastapi.FastAPI(
    title="GeoTrave API",
    description="AI-powered Travel Planning Assistant API",
    version="0.1.0",
    lifespan=lifespan
)

# Register API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    # Start Uvicorn server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

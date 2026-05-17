"""
Module: src.api.routes
Responsibility: Aggregates all API sub-routers into a single unified router.
Parent Module: src.api
Dependencies: fastapi, src.api.chat
"""

from fastapi import APIRouter
from src.api.chat import router as chat_router
from src.api.session import router as session_router

router = APIRouter()
router.include_router(chat_router, prefix="/chat", tags=["Agent Chat"])
router.include_router(session_router, tags=["Session Management"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


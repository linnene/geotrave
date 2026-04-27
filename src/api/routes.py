"""
Module: src.api.routes
Responsibility: Aggregates all API sub-routers into a single unified router.
Parent Module: src.api
Dependencies: fastapi, src.api.chat
"""

from fastapi import APIRouter
from src.api.chat import router as chat_router

router = APIRouter()
router.include_router(chat_router, prefix="/chat", tags=["Agent Chat"])




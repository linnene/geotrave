"""
Module: src.api.routes
Responsibility: Aggregates all API sub-routers (Chat, RAG) into a single unified router.
Parent Module: src.api
Dependencies: fastapi, src.api.chat, src.api.rag
"""

from fastapi import APIRouter
from src.api.chat import router as chat_router
from src.api.rag import router as rag_router

router = APIRouter()

# Combine individual logic routers
router.include_router(chat_router, prefix="/chat", tags=["Agent Chat"])
router.include_router(rag_router, prefix="/rag", tags=["Knowledge Base"])




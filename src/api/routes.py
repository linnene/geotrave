from fastapi import APIRouter
from .chat import router as chat_router
from .rag import router as rag_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(rag_router)



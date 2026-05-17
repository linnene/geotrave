"""
Module: src.api.session
Responsibility: Session metadata CRUD endpoints.
Parent Module: src.api
Dependencies: fastapi, src.api.schema, src.database.session_store
"""

from fastapi import APIRouter, HTTPException

from src.api.schema import CreateSessionRequest, UpdateSessionRequest
from src.database.session_store import SqliteSessionStore
from src.utils import logger

router = APIRouter(prefix="/sessions")


@router.get("/")
async def list_sessions():
    """返回全部会话，按 updated_at 降序排列。"""
    store = await SqliteSessionStore.get_instance()
    sessions = await store.list_all()
    logger.info("[Session API] Listed %d sessions", len(sessions))
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/")
async def create_session(request: CreateSessionRequest):
    """创建新会话。"""
    store = await SqliteSessionStore.get_instance()
    session = await store.create(
        session_id=request.session_id,
        title=request.title,
    )
    logger.info("[Session API] Created session %s", session.session_id)
    return session


@router.patch("/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest):
    """更新会话元数据（title / summary / last_message）。"""
    store = await SqliteSessionStore.get_instance()
    kwargs = {}
    if request.title is not None:
        kwargs["title"] = request.title
    if request.summary is not None:
        kwargs["summary"] = request.summary
    if request.last_message is not None:
        kwargs["last_message"] = request.last_message

    updated = await store.update(session_id, **kwargs)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info("[Session API] Updated session %s", session_id)
    return updated


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话元数据并清理关联的 LangGraph checkpoint。"""
    store = await SqliteSessionStore.get_instance()
    deleted = await store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info("[Session API] Deleted session %s (including checkpoints)", session_id)
    return {"status": "deleted", "session_id": session_id}

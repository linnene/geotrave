"""
Module: src.database.session_store
Responsibility: Session metadata CRUD with encapsulated SQLite storage.
               The abstract interface allows PostgreSQL replacement without
               changing any callers.
Parent Module: src.database
Dependencies: aiosqlite, src.utils.config
"""

import os
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Protocol

import aiosqlite

from src.utils.config import SESSION_DB_PATH, CHECKPOINT_DB_PATH
from src.utils.logger import get_logger

logger = get_logger("SessionStore")


# =============================================================================
# Domain model
# =============================================================================

@dataclass
class SessionMetadata:
    session_id: str
    title: str = ""
    summary: str = ""
    created_at: str = ""
    updated_at: str = ""
    last_message: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# Abstract interface
# =============================================================================

class SessionStore(Protocol):
    """Storage-agnostic session metadata interface."""

    async def create(
        self, session_id: str, title: str = "", summary: str = "",
        last_message: str = "",
    ) -> SessionMetadata: ...

    async def get(self, session_id: str) -> Optional[SessionMetadata]: ...

    async def list_all(self) -> List[SessionMetadata]: ...

    async def update(
        self, session_id: str, **kwargs,
    ) -> Optional[SessionMetadata]: ...

    async def delete(self, session_id: str) -> bool: ...


# =============================================================================
# SQLite implementation
# =============================================================================

DDL = """
CREATE TABLE IF NOT EXISTS session_metadata (
    session_id   TEXT PRIMARY KEY,
    title        TEXT NOT NULL DEFAULT '',
    summary      TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    last_message TEXT NOT NULL DEFAULT ''
)
"""


class SqliteSessionStore:
    """Loop-bound SQLite session metadata store.

    Usage:
        store = await SqliteSessionStore.get_instance()          # default path
        store = await SqliteSessionStore.get_instance(":memory:")  # test
    """

    _instances: dict[asyncio.AbstractEventLoop, "SqliteSessionStore"] = {}
    _db_path: str = SESSION_DB_PATH

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    @classmethod
    async def get_instance(
        cls, db_path: Optional[str] = None,
    ) -> "SqliteSessionStore":
        loop = asyncio.get_running_loop()

        cls._instances = {
            l: inst for l, inst in cls._instances.items()
            if not l.is_closed()
        }

        if loop not in cls._instances:
            path = db_path or cls._db_path
            store = cls(path)
            await store._init()
            cls._instances[loop] = store

        return cls._instances[loop]

    async def _init(self):
        if self._db_path != ":memory:":
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute(DDL)
        await self._conn.commit()
        logger.info("Session store ready at %s", self._db_path)

    async def create(
        self, session_id: str, title: str = "", summary: str = "",
        last_message: str = "",
    ) -> SessionMetadata:
        now = _now_iso()
        await self._conn.execute(
            "INSERT INTO session_metadata VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, title, summary, now, now, last_message),
        )
        await self._conn.commit()
        return SessionMetadata(
            session_id=session_id, title=title, summary=summary,
            created_at=now, updated_at=now, last_message=last_message,
        )

    async def get(self, session_id: str) -> Optional[SessionMetadata]:
        cur = await self._conn.execute(
            "SELECT * FROM session_metadata WHERE session_id = ?", (session_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return SessionMetadata(**dict(row))

    async def list_all(self) -> List[SessionMetadata]:
        cur = await self._conn.execute(
            "SELECT * FROM session_metadata ORDER BY updated_at DESC"
        )
        rows = await cur.fetchall()
        return [SessionMetadata(**dict(r)) for r in rows]

    async def update(
        self, session_id: str, **kwargs,
    ) -> Optional[SessionMetadata]:
        allowed = {"title", "summary", "last_message", "updated_at"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return await self.get(session_id)

        fields.setdefault("updated_at", _now_iso())
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [session_id]

        await self._conn.execute(
            f"UPDATE session_metadata SET {set_clause} WHERE session_id = ?",
            values,
        )
        await self._conn.commit()
        return await self.get(session_id)

    async def delete(self, session_id: str) -> bool:
        cur = await self._conn.execute(
            "DELETE FROM session_metadata WHERE session_id = ?", (session_id,)
        )
        await self._conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            await self._cleanup_checkpoint(session_id)
        return deleted

    async def upsert_on_success(
        self, session_id: str, user_message: str,
        title: Optional[str] = None,
    ) -> SessionMetadata:
        existing = await self.get(session_id)
        if existing:
            return await self.update(
                session_id,
                last_message=user_message,
                updated_at=_now_iso(),
            )
        return await self.create(
            session_id=session_id,
            title=title or (user_message[:50] if user_message else ""),
            last_message=user_message,
        )

    async def _cleanup_checkpoint(self, thread_id: str):
        try:
            async with aiosqlite.connect(CHECKPOINT_DB_PATH) as db:
                for table in (
                    "checkpoint_blobs", "checkpoint_writes", "checkpoints",
                ):
                    await db.execute(
                        f"DELETE FROM {table} WHERE thread_id = ?",
                        (thread_id,),
                    )
                await db.commit()
            logger.info("Cleaned checkpoints for thread %s", thread_id)
        except Exception:
            logger.warning(
                "Failed to clean checkpoints for thread %s",
                thread_id, exc_info=True,
            )

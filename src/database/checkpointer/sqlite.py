"""
Module: src.database.checkpointer.sqlite
Responsibility: Provides specialized SQLite-based persistent storage for LangGraph checkpoints (Async).
Parent Module: src.database.checkpointer
Dependencies: langgraph.checkpoint.sqlite.aio, src.utils.logger
"""

import os
from typing import Optional, Any
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from src.utils.logger import get_logger
from src.utils.config import CHECKPOINT_DB_PATH

logger = get_logger("SqliteCheckpointer")

class SqliteCheckpointer:
    """
    Utility class to manage the lifecycle and instance of an Async SQLite checkpointer.
    """
    _saver_cm: Optional[Any] = None
    _instance: Optional[AsyncSqliteSaver] = None
    _db_path: str = CHECKPOINT_DB_PATH

    @classmethod
    async def get_instance(cls, db_path: Optional[str] = None) -> AsyncSqliteSaver:
        """
        Returns a singleton instance of the AsyncSqliteSaver.
        """
        if db_path:
            cls._db_path = db_path
            
        if cls._instance is None:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cls._db_path), exist_ok=True)
            logger.info(f"Initializing Async SQLite Checkpointer at: {cls._db_path}")
            
            # AsyncSqliteSaver.from_conn_string returns an async context manager
            cls._saver_cm = AsyncSqliteSaver.from_conn_string(cls._db_path)
            # Enter the context manager to get the actual AsyncSqliteSaver instance
            cls._instance = await cls._saver_cm.__aenter__()
            
        if cls._instance is None:
            raise RuntimeError("Failed to initialize AsyncSqliteSaver instance")
            
        return cls._instance

    @classmethod
    async def close(cls):
        """
        Gracefully closes the checkpointer connection.
        """
        if cls._saver_cm:
            logger.info("Closing Async SQLite Checkpointer connection")
            await cls._saver_cm.__aexit__(None, None, None)
            cls._instance = None
            cls._saver_cm = None
    def connection(cls):
        """
        Context manager for clean checkpointer session management.
        """
        checkpointer = cls.get_instance()
        try:
            yield checkpointer
        finally:
            # In SqliteSaver, connection management is mostly internal, 
            # but this provides an extension point for future cleanup logic.
            pass

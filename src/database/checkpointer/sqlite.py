"""
Module: src.database.checkpointer.sqlite
Responsibility: Provides specialized SQLite-based persistent storage for LangGraph checkpoints (Async).
Parent Module: src.database.checkpointer
Dependencies: langgraph.checkpoint.sqlite.aio, src.utils.logger
"""

import os
import asyncio
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
    _bound_loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    async def get_instance(cls, db_path: Optional[str] = None) -> AsyncSqliteSaver:
        """
        Returns a singleton instance of the AsyncSqliteSaver.
        """
        current_loop = asyncio.get_running_loop()
        
        if db_path:
            cls._db_path = db_path
            
        # If the event loop has changed (common in Streamlit/FastAPI hot reloads),
        # we must reset the instance because SQLite/Asyncio locks are bound to the loop.
        if cls._instance is not None and cls._bound_loop != current_loop:
            logger.warning("Event loop changed! Re-initializing SqliteCheckpointer to avoid Lock collision.")
            try:
                # Try to close the old connection context if possible
                if cls._saver_cm:
                    await cls._saver_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error while closing old checkpointer: {e}")
            cls._instance = None
            cls._saver_cm = None

        if cls._instance is None:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cls._db_path), exist_ok=True)
            logger.info(f"Initializing Async SQLite Checkpointer at: {cls._db_path}")
            
            # AsyncSqliteSaver.from_conn_string returns an async context manager
            cls._saver_cm = AsyncSqliteSaver.from_conn_string(cls._db_path)
            # Enter the context manager to get the actual AsyncSqliteSaver instance
            cls._instance = await cls._saver_cm.__aenter__()
            cls._bound_loop = current_loop
            
        if cls._instance is None:
            raise RuntimeError("Failed to initialize AsyncSqliteSaver instance")
            
        return cls._instance

    @classmethod
    async def delete_checkpoint(cls, thread_id: str):
        """
        Deletes all checkpoints associated with a specific thread_id.
        """
        if cls._instance is None:
            await cls.get_instance()
        
        logger.info(f"Cleaning up checkpoints for thread_id: {thread_id}")
        # AsyncSqliteSaver uses a central connection pool. 
        # We can execute raw SQL on the underlying connection.
        if cls._instance is not None:
            async with cls._instance.conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
            ):
                await cls._instance.conn.commit()
            
            async with cls._instance.conn.execute(
                "DELETE FROM writes WHERE thread_id = ?", (thread_id,)
            ):
                await cls._instance.conn.commit()
        else:
            logger.warning("No active AsyncSqliteSaver instance found for cleanup.")

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

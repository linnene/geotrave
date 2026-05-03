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
    _instances: dict[asyncio.AbstractEventLoop, AsyncSqliteSaver] = {}
    _cms: dict[asyncio.AbstractEventLoop, Any] = {}
    _db_path: str = CHECKPOINT_DB_PATH

    @classmethod
    async def get_instance(cls, db_path: Optional[str] = None) -> AsyncSqliteSaver:
        """
        Returns a loop-bound instance of the AsyncSqliteSaver.
        """
        current_loop = asyncio.get_running_loop()
        
        if db_path:
            cls._db_path = db_path
            
        # Clean up stale instances for closed loops
        cls._instances = {loop: inst for loop, inst in cls._instances.items() if not loop.is_closed()}
        cls._cms = {loop: cm for loop, cm in cls._cms.items() if not loop.is_closed()}

        if current_loop not in cls._instances:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cls._db_path), exist_ok=True)
            logger.info(f"Initializing Loop-Bound Async SQLite Checkpointer at: {cls._db_path} for loop {id(current_loop)}")
            
            # AsyncSqliteSaver.from_conn_string returns an async context manager
            cm = AsyncSqliteSaver.from_conn_string(cls._db_path)
            # Enter the context manager to get the actual AsyncSqliteSaver instance
            instance = await cm.__aenter__()
            
            cls._cms[current_loop] = cm
            cls._instances[current_loop] = instance
            
        return cls._instances[current_loop]

    @classmethod
    async def delete_checkpoint(cls, thread_id: str):
        """
        Deletes all checkpoints associated with a specific thread_id.
        """
        instance = await cls.get_instance()
        
        logger.info(f"Cleaning up checkpoints for thread_id: {thread_id}")
        async with instance.conn.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
        ):
            await instance.conn.commit()
        
        async with instance.conn.execute(
            "DELETE FROM writes WHERE thread_id = ?", (thread_id,)
        ):
            await instance.conn.commit()

    @classmethod
    async def close_all(cls):
        """
        Gracefully closes all checkpointer connections.
        """
        for loop, cm in cls._cms.items():
            try:
                if not loop.is_closed():
                    await cm.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error while closing checkpointer for loop {id(loop)}: {e}")
        cls._instances.clear()
        cls._cms.clear()

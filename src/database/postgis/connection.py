"""asyncpg connection pool for PostGIS."""

import asyncio

import asyncpg
from src.database.postgis.config import POSTGIS_DSN

_pool: asyncpg.Pool | None = None
_pool_loop: asyncio.AbstractEventLoop | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the module-level connection pool, creating it on first call.

    Recreates the pool if the current event loop differs from the loop the
    pool was originally created on (e.g. after a uvicorn worker recycle).
    """
    global _pool, _pool_loop
    current_loop = asyncio.get_running_loop()
    if _pool is None or _pool_loop is not current_loop:
        if _pool is not None:
            # 旧池连接附着在已销毁的循环上，无法从当前循环安全关闭；
            # 直接丢弃引用，旧连接由 GC 回收
            _pool = None
        _pool = await asyncpg.create_pool(dsn=POSTGIS_DSN, min_size=2, max_size=8)
        _pool_loop = current_loop
    return _pool


async def close_pool() -> None:
    """Gracefully close the connection pool."""
    global _pool, _pool_loop
    if _pool is not None:
        await _pool.close()
        _pool = None
        _pool_loop = None

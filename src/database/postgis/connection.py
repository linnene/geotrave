"""asyncpg connection pool for PostGIS."""

import asyncpg
from src.database.postgis.config import POSTGIS_DSN

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the module-level connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=POSTGIS_DSN, min_size=2, max_size=8)
    return _pool


async def close_pool() -> None:
    """Gracefully close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

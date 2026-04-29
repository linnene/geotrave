"""
Test Suite: PostGIS Connection Pool
Mapping: /src/database/postgis/connection.py
Priority: P1 - Connection Layer
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_pool_creates_new_pool():
    """
    Priority: P0
    Description: First call to get_pool() creates an asyncpg connection pool
    and records the current event loop.
    """
    mock_pool = AsyncMock()
    with patch("src.database.postgis.connection.asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        import src.database.postgis.connection as conn_mod
        conn_mod._pool = None
        conn_mod._pool_loop = None

        pool = await conn_mod.get_pool()

        assert pool is mock_pool
        assert conn_mod._pool is mock_pool
        assert conn_mod._pool_loop is asyncio.get_running_loop(), (
            "_pool_loop should record the current event loop"
        )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_get_pool_reuses_existing_pool():
    """
    Priority: P1
    Description: Subsequent calls to get_pool() return the same cached pool
    when the event loop hasn't changed.
    """
    mock_pool = AsyncMock()
    current_loop = asyncio.get_running_loop()
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = mock_pool
    conn_mod._pool_loop = current_loop

    pool = await conn_mod.get_pool()

    assert pool is mock_pool


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_pool_recreates_on_loop_mismatch():
    """
    Priority: P0
    Description: get_pool() closes the old pool and creates a new one when
    the current event loop differs from the recorded _pool_loop.
    """
    old_pool = AsyncMock()
    new_pool = AsyncMock()
    old_loop = object()  # sentinel — simulates a different event loop

    with patch("src.database.postgis.connection.asyncpg.create_pool", new=AsyncMock(return_value=new_pool)):
        import src.database.postgis.connection as conn_mod
        conn_mod._pool = old_pool
        conn_mod._pool_loop = old_loop  # mismatched loop

        pool = await conn_mod.get_pool()

        old_pool.close.assert_awaited_once()
        assert pool is new_pool
        assert conn_mod._pool is new_pool
        assert conn_mod._pool_loop is asyncio.get_running_loop()


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_close_pool_releases_and_nulls():
    """
    Priority: P1
    Description: close_pool() calls pool.close() and resets both _pool and
    _pool_loop to None.
    """
    mock_pool = AsyncMock()
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = mock_pool
    conn_mod._pool_loop = asyncio.get_running_loop()

    await conn_mod.close_pool()

    mock_pool.close.assert_awaited_once()
    assert conn_mod._pool is None
    assert conn_mod._pool_loop is None


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_close_pool_none_is_noop():
    """
    Priority: P2
    Description: close_pool() on None pool is a safe no-op.
    """
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = None
    conn_mod._pool_loop = None

    await conn_mod.close_pool()

    assert conn_mod._pool is None
    assert conn_mod._pool_loop is None

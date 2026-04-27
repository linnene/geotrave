"""
Test Suite: PostGIS Connection Pool
Mapping: /src/database/postgis/connection.py
Priority: P1 - Connection Layer
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_pool_creates_new_pool():
    """
    Priority: P0
    Description: First call to get_pool() creates an asyncpg connection pool.
    """
    mock_pool = AsyncMock()
    with patch("src.database.postgis.connection.asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        import src.database.postgis.connection as conn_mod
        conn_mod._pool = None

        pool = await conn_mod.get_pool()

        assert pool is mock_pool, (
            f"首次调用应返回新创建的连接池，预期: {mock_pool}，实际: {pool}"
        )
        assert conn_mod._pool is mock_pool, (
            f"连接池应被缓存到模块级 _pool，预期: {mock_pool}，实际: {conn_mod._pool}"
        )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_get_pool_reuses_existing_pool():
    """
    Priority: P1
    Description: Subsequent calls to get_pool() return the same cached pool.
    """
    mock_pool = AsyncMock()
    with patch("src.database.postgis.connection.asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
        import src.database.postgis.connection as conn_mod
        conn_mod._pool = mock_pool

        pool = await conn_mod.get_pool()

        assert pool is mock_pool, (
            f"已缓存连接池时应直接返回，预期: {mock_pool}，实际: {pool}"
        )


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_close_pool_releases_and_nulls():
    """
    Priority: P1
    Description: close_pool() calls pool.close() and resets _pool to None.
    """
    mock_pool = AsyncMock()
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = mock_pool

    await conn_mod.close_pool()

    mock_pool.close.assert_awaited_once()
    assert conn_mod._pool is None, (
        f"关闭后 _pool 应为 None，实际: {conn_mod._pool}"
    )


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_close_pool_none_is_noop():
    """
    Priority: P2
    Description: close_pool() on None pool is a safe no-op.
    """
    import src.database.postgis.connection as conn_mod
    conn_mod._pool = None

    await conn_mod.close_pool()

    assert conn_mod._pool is None, (
        f"关闭 None pool 应保持 None，实际: {conn_mod._pool}"
    )

"""Shared pytest fixtures for GeoTrave test suite.

Fixtures here are available to all tests without explicit import.
Avoid adding project-specific mocks unless they're used by 3+ test files.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_pool():
    """Mock asyncpg pool yielding (pool, conn) tuple.

    pool.acquire() returns an async context manager whose __aenter__
    yields mock_conn. Set mock_conn.fetch.return_value to control query results.
    """
    mock_conn = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=ctx)
    return pool, mock_conn


@pytest.fixture
def patch_get_pool(mock_pool):
    """Context manager that patches get_pool to return the mock pool."""
    pool, _conn = mock_pool
    target = "src.database.retrieval_db.get_pool"
    return patch(target, new=AsyncMock(return_value=pool))

"""
Test Suite: Retrieval DB
Mapping: /src/database/retrieval_db.py
Priority: P0 - Research Loop persistence layer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# 辅助函数 — 模拟 asyncpg pool/connection 层级
# ---------------------------------------------------------------------------

def _mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """构造 mock pool，其 .acquire() 上下文管理器 yield mock_conn。

    真实 asyncpg 中，pool.acquire() 返回一个既是 awaitable 又是
    async context manager 的对象。此处简化为: .acquire() 同步返回
    一个带有 AsyncMock __aenter__/__aexit__ 的上下文管理器。
    """
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=ctx)
    return pool


def _patch_get_pool(mock_conn: AsyncMock):
    """patch get_pool，使其返回包装了 mock_conn 的 mock pool。"""
    pool = _mock_pool(mock_conn)
    return patch(
        "src.database.retrieval_db.get_pool",
        new=AsyncMock(return_value=pool),
    )


# ---------------------------------------------------------------------------
# P0 — 阻断级测试
# ---------------------------------------------------------------------------

@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_init_retrieval_db_executes_ddl():
    """验证 get_pool 被调用且 DDL 在获取的连接上正确执行。"""
    mock_conn = AsyncMock()

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import init_retrieval_db
        await init_retrieval_db()

    mock_conn.execute.assert_awaited_once()
    ddl_arg = mock_conn.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS retrieval_results" in ddl_arg
    assert "hash_key" in ddl_arg
    assert "payload" in ddl_arg
    assert "session_id" in ddl_arg


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_store_result_insert():
    """验证 payload 被 JSON 序列化后按 hash_key upsert 写入。"""
    mock_conn = AsyncMock()

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import store_result
        await store_result("abc123", "sess-1", {"name": "札幌温泉", "score": 95})

    mock_conn.execute.assert_awaited_once()
    args = mock_conn.execute.call_args
    sql: str = args[0][0]
    params = args[0][1:]

    assert "INSERT INTO retrieval_results" in sql
    assert "ON CONFLICT (hash_key)" in sql
    assert params[0] == "abc123"
    assert params[1] == "sess-1"
    # payload 作为 Python dict 直接传入 (asyncpg 处理 JSONB 序列化)
    assert params[2] == {"name": "札幌温泉", "score": 95}


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_results_returns_payloads():
    """验证按 hash_key 数组批量查询并返回 {hash_key: payload} 映射。"""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {"hash_key": "h1", "payload": {"a": 1}},
        {"hash_key": "h2", "payload": {"b": 2}},
    ]

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import get_results
        result = await get_results(["h1", "h2"])

    assert result == {"h1": {"a": 1}, "h2": {"b": 2}}
    mock_conn.fetch.assert_awaited_once()
    sql = mock_conn.fetch.call_args[0][0]
    assert "SELECT hash_key, payload FROM retrieval_results" in sql
    assert "hash_key = ANY($1)" in sql


# ---------------------------------------------------------------------------
# P1 — 关键测试
# ---------------------------------------------------------------------------

@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_batch_store_results():
    """验证逐条 execute (事务内) 参数正确传递——executemany 对 Python dict→JSONB
    序列化行为不一致，改用逐条 execute + transaction。"""
    mock_conn = AsyncMock()
    # 使 conn.transaction() 返回合法的 async context manager
    _tx_ctx = MagicMock()
    _tx_ctx.__aenter__ = AsyncMock(return_value=None)
    _tx_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=_tx_ctx)

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import batch_store_results
        await batch_store_results(
            [
                {"hash_key": "h1", "payload": {"x": 10}},
                {"hash_key": "h2", "payload": {"y": 20}},
            ],
            session_id="sess-batch",
        )

    # 验证事务被启用
    mock_conn.transaction.assert_called_once()

    # 验证逐条 execute（2 条结果 = 2 次 execute）
    assert mock_conn.execute.await_count == 2

    sql_0 = mock_conn.execute.call_args_list[0][0][0]
    params_0 = mock_conn.execute.call_args_list[0][0][1:]
    assert "INSERT INTO retrieval_results" in sql_0
    assert "ON CONFLICT (hash_key)" in sql_0
    assert params_0[0] == "h1"
    assert params_0[1] == "sess-batch"
    assert params_0[2] == {"x": 10}

    sql_1 = mock_conn.execute.call_args_list[1][0][0]
    params_1 = mock_conn.execute.call_args_list[1][0][1:]
    assert params_1[0] == "h2"
    assert params_1[1] == "sess-batch"
    assert params_1[2] == {"y": 20}


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_cleanup_session():
    """验证按 session_id 删除所有关联行。"""
    mock_conn = AsyncMock()

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import cleanup_session
        await cleanup_session("sess-cleanup")

    mock_conn.execute.assert_awaited_once()
    sql = mock_conn.execute.call_args[0][0]
    params = mock_conn.execute.call_args[0][1:]
    assert "DELETE FROM retrieval_results" in sql
    assert "session_id = $1" in sql
    assert params[0] == "sess-cleanup"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_get_results_empty_list_short_circuits():
    """验证空列表输入直接返回 {}，不访问数据库。"""
    mock_conn = AsyncMock()

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import get_results
        result = await get_results([])

    assert result == {}
    mock_conn.fetch.assert_not_called()


# ---------------------------------------------------------------------------
# P2 — 边界测试
# ---------------------------------------------------------------------------

@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_get_results_partial_match():
    """验证仅返回匹配的 hash_key，缺失的 key 不出现在结果中。"""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {"hash_key": "h1", "payload": {"z": 99}},
    ]

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import get_results
        result = await get_results(["h1", "h_missing"])

    assert result == {"h1": {"z": 99}}
    assert "h_missing" not in result


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_store_result_overwrite():
    """验证同一 hash_key 再次写入会覆盖旧 payload（upsert 语义）。"""
    mock_conn = AsyncMock()

    with _patch_get_pool(mock_conn):
        from src.database.retrieval_db import store_result
        await store_result("dup_key", "sess", {"v": 1})
        await store_result("dup_key", "sess", {"v": 2})

    assert mock_conn.execute.await_count == 2
    # 两次调用使用相同的 hash_key
    for call in mock_conn.execute.call_args_list:
        assert call[0][1] == "dup_key"

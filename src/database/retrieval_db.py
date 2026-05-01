"""
Module: src.database.retrieval_db
Responsibility: PostgreSQL JSONB persistence for Research Loop retrieval results.
Parent Module: src.database
Dependencies: asyncpg, src.database.postgis.connection

Hash-keyed result storage so the parent graph only exposes {query: [hash_key, ...]};
full payloads stay in PostgreSQL and are fetched on demand by Recommender / Planner.
"""

import json
from typing import Dict, List, Any

from src.database.postgis.connection import get_pool


_RETRIEVAL_TABLE = "retrieval_results"

_INIT_DDL = f"""
CREATE TABLE IF NOT EXISTS {_RETRIEVAL_TABLE} (
    hash_key    TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_retrieval_session ON {_RETRIEVAL_TABLE} (session_id);
"""


async def init_retrieval_db() -> None:
    """创建检索结果表及索引（如不存在）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_INIT_DDL)


async def store_result(hash_key: str, session_id: str, payload: Dict[str, Any]) -> None:
    """写入单条检索结果（按 hash_key  upsert）。

    asyncpg 不会自动将 Python dict 序列化为 JSONB——必须先用 json.dumps
    转为字符串，再通过 $3::jsonb 强制 PostgreSQL 解析为 JSONB 对象。
    仅 json.dumps 而不加 ::jsonb 会导致存储为 JSON 字符串而非对象。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"INSERT INTO {_RETRIEVAL_TABLE} (hash_key, session_id, payload) "
            "VALUES ($1, $2, $3::jsonb) "
            "ON CONFLICT (hash_key) DO UPDATE SET payload = $3::jsonb",
            hash_key, session_id, json.dumps(payload, ensure_ascii=False),
        )


async def batch_store_results(
    results: List[Dict[str, Any]], session_id: str
) -> None:
    """批量写入结果。每条 dict 必须包含 'hash_key' 和 'payload' 键。

    asyncpg 不会自动将 Python dict 序列化为 JSONB——必须先用 json.dumps
    转为字符串，再通过 $3::jsonb 强制 PostgreSQL 解析为 JSONB 对象。"""
    if not results:
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for r in results:
                await conn.execute(
                    f"INSERT INTO {_RETRIEVAL_TABLE} (hash_key, session_id, payload) "
                    "VALUES ($1, $2, $3::jsonb) "
                    "ON CONFLICT (hash_key) DO UPDATE SET payload = $3::jsonb",
                    r["hash_key"], session_id,
                    json.dumps(r["payload"], ensure_ascii=False),
                )


async def get_results(hash_keys: List[str]) -> Dict[str, Dict[str, Any]]:
    """按 hash_key 批量查询 payload。返回 {hash_key: payload}。"""
    if not hash_keys:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT hash_key, payload FROM {_RETRIEVAL_TABLE} WHERE hash_key = ANY($1)",
            hash_keys,
        )
    return {row["hash_key"]: row["payload"] for row in rows}


async def cleanup_session(session_id: str) -> None:
    """删除指定会话的所有检索结果。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"DELETE FROM {_RETRIEVAL_TABLE} WHERE session_id = $1", session_id
        )

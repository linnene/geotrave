"""BM25 文档检索引擎 — 内存索引 + PostgreSQL 持久化。

文档内容不可变，SHA256(内容) 生成 doc_id 即 retrieval_db 的 hash_key。
内存只存 BM25 所需 tokenized corpus + 轻量元数据，全文在 PostgreSQL 按需取出。
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from src.utils.logger import get_logger
from .config import BM25_K1, BM25_B, BM25_SCORE_THRESHOLD, MAX_DOC_RESULTS

logger = get_logger("DocumentManager")

_SESSION_SYSTEM = "_system"
_PREVIEW_LEN = 400


def _tokenize(text: str) -> List[str]:
    """简单中英文混合分词。"""
    tokens: List[str] = []
    for chunk in re.split(r"[\s,.\-/:;!?()（），。、；：！“”…—\n\r\t]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if all(ord(c) < 128 for c in chunk):
            tokens.append(chunk.lower())
        else:
            for c in chunk:
                if c.strip():
                    tokens.append(c)
    return tokens


def _gen_doc_id(content: str) -> str:
    return "doc_" + hashlib.sha256(content.encode()).hexdigest()[:16]


class DocumentManager:
    """内存 BM25 文档检索引擎。

    全文仅存在于 PostgreSQL retrieval_db（key = doc_id）。
    内存保留 tokenized 语料 + 元数据列表（与索引顺序对齐）。
    """

    def __init__(self):
        self._bm25: Optional[BM25Okapi] = None
        self._corpus: List[List[str]] = []  # tokenized 语料，ingest 增量需要
        self._doc_ids: List[str] = []       # 与 BM25 行对齐
        self._titles: List[str] = []
        self._place_names: List[str] = []
        self._sources: List[str] = []
        self._previews: List[str] = []      # 前 _PREVIEW_LEN 字符，用于片段

    @property
    def is_loaded(self) -> bool:
        return self._bm25 is not None

    def doc_count(self) -> int:
        return len(self._doc_ids)

    # ------------------------------------------------------------------
    # 索引构建（启动时从 PostgreSQL 加载）
    # ------------------------------------------------------------------

    async def build_index(self, pool) -> None:
        from src.database.retrieval_db import _RETRIEVAL_TABLE

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT hash_key, payload FROM {_RETRIEVAL_TABLE} WHERE session_id = $1",
                _SESSION_SYSTEM,
            )

        if not rows:
            logger.info("DocumentManager: 无系统文档，索引为空")
            # BM25Okapi 不支持空语料，is_loaded=False 时 search 返回空列表
            return

        corpus: List[List[str]] = []
        for row in rows:
            doc_id = row["hash_key"]
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            content = payload.get("content", "")
            title = payload.get("title", "")
            place_name = payload.get("place_name", "")

            full_text = f"{title} {place_name} {content}"
            tokens = _tokenize(full_text)
            if not tokens:
                continue

            corpus.append(tokens)
            self._doc_ids.append(doc_id)
            self._titles.append(title)
            self._place_names.append(place_name)
            self._sources.append(payload.get("source", ""))
            self._previews.append(content[:_PREVIEW_LEN])

        self._corpus = corpus
        self._bm25 = BM25Okapi(corpus, k1=BM25_K1, b=BM25_B)
        logger.info(f"DocumentManager: 加载完成，共 {len(self._doc_ids)} 篇文档")

    # ------------------------------------------------------------------
    # 检索（只返回元数据，不含全文）
    # ------------------------------------------------------------------

    def search(
        self, query: str, place_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """BM25 检索，按相关度阈值 + 可选地名过滤。

        Returns:
            [{doc_id, title, place_name, source, score, snippet}]
            不含全文——下游通过 retrieval_db.get_results([doc_id]) 按需取出。
        """
        if not self._bm25 or not self._doc_ids:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        candidates: List[tuple[int, float]] = []
        for i, score in enumerate(scores):
            if score < BM25_SCORE_THRESHOLD:
                continue
            if place_filter:
                if place_filter.lower() not in (self._place_names[i] or "").lower():
                    continue
            candidates.append((i, float(score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:MAX_DOC_RESULTS]

        return [
            {
                "doc_id": self._doc_ids[i],
                "title": self._titles[i],
                "place_name": self._place_names[i],
                "source": self._sources[i],
                "score": round(score, 4),
                "snippet": self._previews[i],
            }
            for i, score in candidates
        ]

    # ------------------------------------------------------------------
    # 文档入库（离线管线调用）
    # ------------------------------------------------------------------

    async def ingest(
        self, content: str, metadata: Dict[str, Any], pool
    ) -> str:
        """写入 PostgreSQL + 增量更新内存 BM25 索引。"""
        from src.database.retrieval_db import store_result

        doc_id = _gen_doc_id(content)

        payload = {**metadata, "content": content, "doc_id": doc_id}
        await store_result(doc_id, _SESSION_SYSTEM, payload)

        title = metadata.get("title", "")
        place_name = metadata.get("place_name", "")
        full_text = f"{title} {place_name} {content}"
        tokens = _tokenize(full_text)

        if tokens and self._bm25 is not None:
            self._doc_ids.append(doc_id)
            self._titles.append(title)
            self._place_names.append(place_name)
            self._sources.append(metadata.get("source", ""))
            self._previews.append(content[:_PREVIEW_LEN])
            # 重建索引（rank-bm25 不支持增量，但文档量小可接受全量重建）
            self._corpus.append(tokens)
            self._bm25 = BM25Okapi(self._corpus, k1=BM25_K1, b=BM25_B)

        logger.info(f"DocumentManager: 入库完成 doc_id={doc_id}")
        return doc_id


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_document_manager: Optional[DocumentManager] = None


async def get_document_manager(pool) -> DocumentManager:
    global _document_manager
    if _document_manager is None:
        _document_manager = DocumentManager()
        await _document_manager.build_index(pool)
    return _document_manager

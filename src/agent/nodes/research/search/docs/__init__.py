"""BM25 文档检索引擎 — 内存索引 + PostgreSQL 持久化。"""

from .manager import DocumentManager, get_document_manager

__all__ = ["DocumentManager", "get_document_manager"]

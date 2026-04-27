"""
Module: src.api.schema
Responsibility: Defines Pydantic models for API request and response validation.
Parent Module: src.api
Dependencies: pydantic

Refactoring Note: All descriptions must be in Chinese per project requirements.
"""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, Field

# ---------- 对话模型 ----------

class ChatRequest(BaseModel):
    """用户对话请求模型"""
    message: str = Field(
        ...,
        min_length=1,
        description="用户输入的消息内容，不能为空"
    )
    session_id: str = Field(
        default="default_session",
        description="对话会话 ID，用于在 LangGraph 中维护历史上下文"
    )

class ChatResponse(BaseModel):
    """对话响应模型"""
    response: str = Field(
        ...,
        description="助手返回的回复内容"
    )
    session_id: str = Field(
        ...,
        description="本次对话的会话 ID"
    )

# ---------- RAG 模型 ----------

class DocumentItem(BaseModel):
    """单个 RAG 文档条目"""
    content: str = Field(
        ...,
        description="要写入向量库的文本内容"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="与文档关联的元数据字典"
    )

class InsertRequest(BaseModel):
    """批量插入 RAG 文档的请求模型"""
    documents: List[DocumentItem] = Field(
        ...,
        description="待插入的文档对象列表"
    )

class InsertResponse(BaseModel):
    """批量插入 RAG 文档的响应模型"""
    status: str = Field(
        default="ok",
        description="操作状态，固定为 ok"
    )
    inserted_count: int = Field(
        ...,
        description="成功插入的文档数量"
    )

class SearchRequest(BaseModel):
    """RAG 相似度检索请求模型"""
    query: str = Field(
        ...,
        description="用于在向量数据库中进行语义检索的查询文本"
    )
    k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="返回的相似文档数量限制，默认为 3，最大为 10"
    )

class SearchResult(BaseModel):
    """单个检索结果"""
    content: str = Field(
        ...,
        description="文档内容"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="文档元数据"
    )
    score: float = Field(
        ...,
        description="相似度得分"
    )

class SearchResponse(BaseModel):
    """RAG 相似度检索响应模型"""
    results: List[SearchResult] = Field(
        ...,
        description="检索到的文档列表"
    )

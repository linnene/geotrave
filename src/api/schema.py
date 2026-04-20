"""
Module: src.api.schema
Responsibility: Defines Pydantic models for API request and response validation.
Parent Module: src.api
Dependencies: pydantic

Refactoring Note: All descriptions must be in Chinese per project requirements.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """
    用户对话请求模型
    """
    message: str = Field(
        ..., 
        min_length=1, 
        description="用户输入的消息内容，不能为空"
    )
    session_id: str = Field(
        default="default_session", 
        description="对话会话 ID，用于在 LangGraph 中维护历史上下文"
    )

class DocumentItem(BaseModel):
    """
    单个 RAG 文档条目
    """
    content: str = Field(
        ..., 
        description="要写入向量库的文本内容"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="与文档关联的元数据字典"
    )

class InsertRequest(BaseModel):
    """
    批量插入 RAG 文档的请求模型
    """
    documents: List[DocumentItem] = Field(
        ..., 
        description="待插入的文档对象列表"
    )

class SearchRequest(BaseModel):
    """
    RAG 相似度检索请求模型
    """
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

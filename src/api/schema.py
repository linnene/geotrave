"""
Module: src.api.schema
Responsibility: Defines Pydantic models for API request and response validation.
Parent Module: src.api
Dependencies: pydantic

Refactoring Note: All descriptions must be in Chinese per project requirements.
"""

from typing import Any, Dict, List, Optional
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
    """Agent 对话响应模型"""
    reply: str = Field(..., description="AI 回复文本")
    session_id: str = Field(..., description="会话 ID")
    status: str = Field(..., description="状态: success | error")
    route: Optional[Dict[str, Any]] = Field(None, description="当前路由元数据")
    signs: Optional[Dict[str, Any]] = Field(None, description="执行信号标记")
    trace: Optional[List[Dict[str, Any]]] = Field(None, description="节点审计轨迹")
    profile: Optional[Dict[str, Any]] = Field(None, description="用户画像")
    recommendation: Optional[Any] = Field(None, description="推荐数据")
    plan: Optional[Any] = Field(None, description="行程规划数据")


# ---------- 会话管理模型 ----------

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    session_id: str = Field(..., min_length=1, description="会话 ID")
    title: str = Field(default="新对话", description="会话标题")


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(None, description="新标题")
    summary: Optional[str] = Field(None, description="会话摘要")
    last_message: Optional[str] = Field(None, description="最后一条消息")


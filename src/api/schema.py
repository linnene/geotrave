"""
Module: src.api.schema
Responsibility: Defines Pydantic models for API request and response validation.
Parent Module: src.api
Dependencies: pydantic

Refactoring Note: All descriptions must be in Chinese per project requirements.
"""

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



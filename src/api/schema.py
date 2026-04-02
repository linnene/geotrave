from pydantic import BaseModel, Field

#用户输入消息格式
class ChatRequest(BaseModel):
    """
    用户输入消息的请求体格式
    """
    message: str = Field(..., min_length=1, description="用户输入的消息内容")

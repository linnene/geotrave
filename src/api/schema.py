from pydantic import BaseModel, Field
from typing import List


#用户输入消息格式
class ChatRequest(BaseModel):
    
    """
    用户输入消息的请求体格式
    """

    message: str = Field(..., min_length=1, description="用户输入的消息内容")


# RAG 写入接口请求体格式
class DocumentItem(BaseModel):
    content: str = Field(..., description="要写入的文本内容")
    metadata: dict = Field(default_factory=dict, description="伴随条目的元数据")

class InsertRequest(BaseModel):
    documents: List[DocumentItem]
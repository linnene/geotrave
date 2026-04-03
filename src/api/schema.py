#TODO:完善用户输入请求体格式
from pydantic import BaseModel, Field
from typing import List



# ----------user_Enter_mes格式-----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入的消息内容")
    session_id: str = Field(default="default_session", description="对话会话 ID，用于维护历史上下文")
# ----------user_Enter_mes格式-----------

# ---------RAG 写入接口请求体格式---------
class DocumentItem(BaseModel):
    content: str = Field(..., description="要写入的文本内容")
    metadata: dict = Field(default_factory=dict, description="伴随条目的元数据")

class InsertRequest(BaseModel):
    documents: List[DocumentItem]

class SearchRequest(BaseModel):
    query: str = Field(..., description="用于检索的查询文本")
    k: int = Field(default=3, description="返回的相似文档数量，默认为3")
# ---------RAG 写入接口请求体格式---------
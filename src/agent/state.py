from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# 共享“白板” (State)
class TravelState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] # 消息历史
    destination: str | None # 目的地
    days: int | None        # 天数
    budget: int | None      # 预算


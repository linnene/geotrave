from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict
from pydantic import BaseModel, Field


# shared State
class TravelState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] # history of conversation, including both user and assistant messages

    destination: str | None # destination
    days: int | None        # days of travel
    date: list[str] | None        # date range of travel, format: [YYYY-MM-DD,YYYY-MM-DD]

    budget: int | None      # budget of travel
    people: int | None      # number of people traveling
    retrieval_context: str | None # context retrieved from RAG


# Analyzer Node databar
class TravelInfo(BaseModel):
    destination: str | None = Field(default=None, description="旅行目的地，如果没有则为None")
    days: int | None = Field(default=None, description="旅行天数，如果没有则为None")
    date: list[str] | None = Field(
        default=None, 
        min_length=2, 
        max_length=2, 
        description="旅行日期，格式为[YYYY-MM-DD,YYYY-MM-DD] ([开始日期, 结束日期])，例如 ['2026-04-01', '2026-04-07']"
    )
    
    budget: int | None = Field(default=None, description="旅行总预算")
    peoples: int | None = Field(default= 1, description="旅行总人数，默认一个人")

    reply: str = Field(description="如果信息不全，请客气地像导游一样追问缺失的信息。")
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict, List, Dict, Optional, Any

# ----------------- Con Models -----------------

class UserProfileState(TypedDict):
    """扁平化的用户画像（合并基础信息与次要偏好）"""
    destination: list[str] | None
    days: int | None
    date: list[str] | None
    people_count: int | None
    budget_limit: int | None
    accommodation: str | None
    dining: str | None
    transportation: str | None
    pace: str | None
    activities: list[str] | None
    preferences: list[str]
    avoidances: list[str]

class RetrievalItem(TypedDict):
    """单条检索结果项（改为 TypedDict 避免 checkpointer msgpack 序列化报错）"""
    source: str
    title: str
    content: str
    link: Optional[str]
    metadata: Dict[str, Any]

# ----------------- Shared State -----------------

class SearchState(TypedDict):
    """解耦的私有搜索状态，仅在检索、推荐和计划节点流转"""
    query_history: list[str] | None
    retrieval_context: str | None
    retrieval_results: list[RetrievalItem] | None

class RecommenderState(TypedDict):
    """解耦的私有推荐状态，仅由推荐和计划节点维护"""
    recommended_items: list[dict] | None
    user_selected_items: list[dict] | None


class TravelState(TypedDict):
    """全局状态白板"""
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Router识别出来的最新用户意图，用于条件边分发
    latest_intent: str | None
    
    # Anaslyzer判定的标志位，决定是否唤起检索节点
    needs_research: bool | None
    
    # 用户需求（由于扁平化，合并为一个 profile）
    user_profile: UserProfileState | None
    
    #检索结果
    search_data: SearchState | None
    #推荐结果
    recommender_data: RecommenderState | None

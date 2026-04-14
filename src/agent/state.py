from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict, List, Dict, Optional, Any

# ----------------- Con Models -----------------

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
    last_searched_req: dict | None  # 记录上一次检索时的全局需求特征快照

class RecommenderState(TypedDict):
    """解耦的私有推荐状态，仅由推荐和计划节点维护"""
    recommended_items: list[dict] | None
    user_selected_items: list[dict] | None

class CoreRequirementState(TypedDict):
    """用户核心旅游需求（解耦后的基础信息）"""
    destination: list[str] | None
    days: int | None
    date: list[str] | None
    people: list[str] | None
    budget_limit: int | None

class SecondaryPreferencesState(TypedDict):
    """用户次要需求/偏好（细粒度的结构化分类，避免重叠冲突）"""
    accommodation: str | None
    dining: str | None
    transportation: str | None
    pace: str | None  # 游玩节奏，例如"休闲", "紧凑/特种兵"
    activities: list[str] | None  # 兴趣活动，例如"看海", "购物", "博物馆"

class ConversationSummaryState(TypedDict):
    """对话总结与约束维护：由分析师维护的细粒度偏好池（解决重叠问题，简化为正面偏好和负面避雷）"""
    preferences: list[str]
    avoidances: list[str]

class TravelState(TypedDict):
    """全局状态白板"""
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 意图路由节点识别出来的最新用户意图，用于条件边分发
    latest_intent: str | None
    
    # 分析师判定的标志位，决定是否唤起检索节点
    needs_research: bool | None
    
    # 彻底解耦的各个模块数据
    core_requirements: CoreRequirementState | None
    secondary_preferences: SecondaryPreferencesState | None
    conversation_summary: ConversationSummaryState | None
    search_data: SearchState | None
    recommender_data: RecommenderState | None

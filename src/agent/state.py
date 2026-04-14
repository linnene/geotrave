from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field

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
    tags: list[str] | None

class ConversationSummaryState(TypedDict):
    """对话总结与约束维护：由分析师维护的细粒度偏好池"""
    core_constraints: list[str]
    temp_preferences: list[str]
    rejected_items: list[str]

class TravelState(TypedDict):
    """全局状态白板"""
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 意图路由节点识别出来的最新用户意图，用于条件边分发
    latest_intent: str | None
    
    # 分析师判定的标志位，决定是否唤起检索节点
    needs_research: bool | None
    
    # 彻底解耦的各个模块数据
    core_requirements: CoreRequirementState | None
    conversation_summary: ConversationSummaryState | None
    search_data: SearchState | None
    recommender_data: RecommenderState | None

# ----------------- Analyzer node -----------------

class ConversationSummary(BaseModel):
    """分析师输出的总结数据，用于转换为 TypedDict"""
    core_constraints: List[str] = Field(default_factory=list, description="用户提到的核心硬性约束/要求")
    temp_preferences: List[str] = Field(default_factory=list, description="用户的临时偏好或随口一提的兴趣")
    rejected_items: List[str] = Field(default_factory=list, description="用户已明确否定/不喜欢/拒绝的选项")

class TravelInfo(BaseModel):
    """分析师输出的结构化数据"""
    destination: List[str] = Field(default_factory=list, description="目的地列表(支持多个)")
    days: Optional[int] = Field(None, description="天数")
    date: Optional[List[Optional[str]]] = Field(None, min_length=2, max_length=2)
    people_count: Optional[int] = Field(default=1)
    budget_limit: Optional[int] = Field(default=0)
    tags: List[str] = Field(default_factory=list)
    conversation_summary: ConversationSummary = Field(default_factory=ConversationSummary)
    needs_research: bool = Field(default=False, description="是否需要主动唤起检索节点（比如核心需求刚凑全、或者发生了关键变更使得旧信息不再适用时设为True）")
    reply: str = Field(description="追问User")

# ----------------- Researcher node -----------------

class ResearchPlan(BaseModel):
    """研究员生成的检索计划"""
    local_query: Optional[str] = Field(description="知识库检索关键词")
    web_queries: List[str] = Field(default_factory=list, description="在线搜索关键词")
    need_weather: bool = Field(default=False)
    need_api: List[str] = Field(default_factory=list)

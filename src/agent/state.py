from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict, List, Dict, Optional
from pydantic import BaseModel, Field

# ----------------- Con Models -----------------

class HardConstraints(BaseModel):
    """硬约束集合：具有一票否决权的信息"""
    budget_limit: Optional[int] = Field(None, description="预算绝对上限")
    max_walk_km: Optional[float] = Field(None, description="每日最大步行距离（km）")
    visa_restrictions: List[str] = Field(default_factory=list, description="签证或证件限制")
    allergies: List[str] = Field(default_factory=list, description="明确的过敏史")
    locked_resources: List[Dict] = Field(default_factory=list, description="已锁定的资源")

class SoftPreferences(BaseModel):
    """软偏好集合：用于加权评分的信息"""
    travel_pace: Optional[str] = Field(None, description="旅行节奏")
    interests: List[str] = Field(default_factory=list, description="偏好主题")
    dietary_pref: List[str] = Field(default_factory=list, description="餐饮偏好")
    accommodation_type: List[str] = Field(default_factory=list, description="住宿偏好")

class RetrievalItem(BaseModel):
    """单条检索结果项"""
    source: str = Field(..., description="来源标识: local, web, weather 等")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="具体内容/摘要")
    link: Optional[str] = Field(None, description="原始链接")
    metadata: Dict = Field(default_factory=dict, description="额外元数据")

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
    destination: str | None
    days: int | None
    date: list[str] | None
    people: list[str] | None
    budget_limit: int | None
    hard_constraints: HardConstraints
    soft_preferences: SoftPreferences
    tags: list[str] | None
    
    # 使用独立的属性存储子图或节点专用的私有状态，不污染公共白板
    search_data: SearchState | None
    recommender_data: RecommenderState | None

# ----------------- Analyzer node -----------------

class TravelInfo(BaseModel):
    """分析师输出的结构化数据"""
    destination: Optional[str] = Field(None, description="目的地")
    days: Optional[int] = Field(None, description="天数")
    date: Optional[List[Optional[str]]] = Field(None, min_length=2, max_length=2)
    people_count: Optional[int] = Field(default=1)
    budget_limit: Optional[int] = Field(default=0)
    hard_constraints: HardConstraints = Field(default_factory=HardConstraints)
    soft_preferences: SoftPreferences = Field(default_factory=SoftPreferences)
    tags: List[str] = Field(default_factory=list)
    reply: str = Field(description="话术回复")

# ----------------- Researcher node -----------------

class ResearchPlan(BaseModel):
    """研究员生成的检索计划"""
    local_query: Optional[str] = Field(description="知识库检索关键词")
    web_queries: List[str] = Field(default_factory=list, description="在线搜索关键词")
    need_weather: bool = Field(default=False)
    need_api: List[str] = Field(default_factory=list)

# ----------------- Filter node -----------------
class EvaluationResult(BaseModel):
    """单条检索结果的判定模型"""
    is_safe: bool = Field(..., description="内容是否合规")
    is_relevant: bool = Field(..., description="内容是否相关")
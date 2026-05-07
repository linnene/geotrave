"""LLM 输出契约 — 每个 LLM 驱动节点的 JSON 解析契约。

这些模型不是领域 State，而是节点与 LLM 之间的结构化协议。
节点解析 LLM 输出后自行提取字段写入全局 State。
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from typing import Literal

from .domain import UserProfile, SearchTask


class GatewayOutput(BaseModel):
    """Gateway 节点结构化输出。"""
    is_valid: bool = Field(..., description="Whether the input is valid and compliant")
    category: Literal["legal", "malicious", "chitchat"] = Field(
        ..., description="Intent classification"
    )
    reason: str = Field(..., description="Brief rationale for the classification")
    reply: str = Field(
        default="",
        description="Rejection reply when invalid; PII-sanitised text when legal with sensitive info"
    )
    sanitized_text: Optional[str] = Field(
        default=None,
        description="PII-sanitised user input; None if no PII detected"
    )


class AnalystOutput(BaseModel):
    """Analyst 节点结构化输出。"""
    updated_profile: UserProfile = Field(
        ..., description="Merged and updated UserProfile after this round"
    )
    missing_fields: List[str] = Field(
        default_factory=list, description="Fields still missing from UserProfile"
    )
    reason: str = Field(..., description="Brief explanation of extraction and merge logic")


class ManagerOutput(BaseModel):
    """Manager 节点结构化输出 — 控制全局路由。"""
    next_stage: Literal["research_loop", "recommender", "planner", "reply"] = Field(
        ...,
        description=(
            "Next routing target. research_loop: execute research subgraph (QG->Search->Critic<->QG|Hash); "
            "recommender: recommend items; planner: generate itinerary; reply: respond to user"
        )
    )
    rationale: str = Field(..., description="Detailed logic behind this routing decision")
    focus_dimension: Optional[str] = Field(
        default=None,
        description="When user explicitly requests a specific recommendation dimension, set this to guide Recommender (any dimension, e.g. 'attraction', 'shopping', 'food', 'accommodation')"
    )


class QueryGeneratorOutput(BaseModel):
    """QueryGenerator 节点结构化输出。"""
    tasks: List[SearchTask] = Field(..., description="Decomposed multi-dimension search task list")
    research_strategy: str = Field(
        ...,
        description="Overall research strategy narrative, e.g. '先通过通用搜索确定热门商圈，再针对性检索高评分民宿'"
    )


class DimensionItem(BaseModel):
    """单个调研维度规划。"""
    name: str = Field(
        ..., description="Dimension name — freely chosen based on user intent (e.g. ski_resort, hot_spring, shopping, local_festival, nightlife). Use lowercase English with underscores."
    )
    focus: str = Field(..., description="What specifically to search for in this dimension")
    priority: int = Field(default=3, ge=1, le=5, description="Priority 1-5, higher = more urgent")


class DimensionPlannerOutput(BaseModel):
    """DimensionPlanner 节点结构化输出。"""
    dimensions: List[DimensionItem] = Field(..., description="Decomposed research dimensions")
    rationale: str = Field(..., description="Why these dimensions were chosen")

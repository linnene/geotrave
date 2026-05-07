"""业务领域模型 — 用户画像与搜索任务定义。"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Analyst 提取的结构化旅行偏好与约束。"""
    destination: List[str] = Field(default_factory=list, description="Destination names")
    days: Optional[int] = Field(None, description="Trip duration in days")
    date: Optional[List[str]] = Field(None, description="Date range [start, end]")
    people_count: Optional[int] = Field(1, description="Number of travellers")
    budget_limit: Optional[int] = Field(0, description="Total budget upper bound")

    # 软偏好
    accommodation: Optional[str] = Field(None, description="Accommodation style preference")
    dining: Optional[str] = Field(None, description="Dietary restrictions or cuisine preference")
    transportation: Optional[str] = Field(None, description="Transport mode preference")
    pace: Optional[str] = Field(None, description="Trip pace: relaxed / balanced / packed")

    # 无法归入固定字段的信号溢出袋
    Flex: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Overflow for unstructured preferences not covered by named fields"
    )

    # Analyst 写入的缺失字段列表，供 Reply/QG 读取，消除 TravelState 顶层字段
    all_missing_fields: List[str] = Field(
        default_factory=list,
        description="All fields still missing from UserProfile; set by Analyst, consumed by Reply and QueryGenerator"
    )

    def check_completeness(self) -> tuple[bool, List[str]]:
        """审计画像完备性。

        返回:
            (is_core_complete, all_missing_fields)

        核心字段决定是否可启动调研:
            destination, days/date, people_count, budget_limit。
        完整缺失字段列表供 Reply 节点引导用户补充信息。

        调用方应在调用后将 all_missing_fields 写入模型字段。
        """
        core_missing: List[str] = []
        if not self.destination:
            core_missing.append("destination")
        if not self.days and not self.date:
            core_missing.append("days_or_date")
        if not self.people_count:
            core_missing.append("people_count")
        if self.budget_limit is None:
            core_missing.append("budget_limit")

        is_core_complete = len(core_missing) == 0

        all_missing: List[str] = []
        for field_name in type(self).model_fields.keys():
            if field_name in ("Flex", "all_missing_fields"):
                continue
            val = getattr(self, field_name)
            if val is None or val == "" or val == [] or val == 0:
                all_missing.append(field_name)

        return is_core_complete, all_missing


class SearchTask(BaseModel):
    """QueryGenerator 发出的单条工具调用指令。"""
    tool_name: str = Field(
        ...,
        description="Target tool: spatial_search / route_search"
    )
    dimension: str = Field(
        ..., description="Research dimension this task addresses — freely named to match the focus dimension (e.g. ski_resort, shopping, weather, dining)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific arguments."
    )
    rationale: str = Field(..., description="Why this task was generated and what it should yield")


class RetrievalMetadata(BaseModel):
    """工具 handler 返回的原始检索结果信封。

    Search 节点读取 payload 字段后包裹为 ResearchResult 送入 Critic，
    不再直接暴露给父图。hash_key 仅用于工具内部追踪。
    """
    hash_key: str = Field(..., description="Content-addressable key for KV store lookup")
    source: str = Field(..., description="Data source label or URL")
    relevance_score: float = Field(default=0.0, description="Critic-assigned relevance score")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Full result payload")

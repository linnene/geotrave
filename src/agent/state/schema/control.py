"""控制面模型 — 路由信号、跨节点布尔标记、审计轨迹。"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RouteMetadata(BaseModel):
    """控制面路由指令，仅由 Manager 写入。"""
    next_node: str = Field(..., description="Target node name for the next hop")
    reason: str = Field(..., description="Rationale behind the routing decision")
    focus_dimension: Optional[str] = Field(default=None, description="Manager: explicit dimension hint for recommender (any domain-appropriate dimension)")


class ExecutionSigns(BaseModel):
    """跨节点信号面 — 各业务节点设置的布尔标记。"""
    is_safe: bool = Field(default=True, description="Gateway: input passed safety check")
    is_core_complete: bool = Field(default=False, description="Analyst: core profile fields sufficient")
    is_recommendation_complete: bool = Field(default=False, description="Recommender: all requested recommendation dimensions covered")
    is_plan_complete: bool = Field(default=False, description="Planner: day-by-day itinerary generated")
    recommended_dimensions: List[str] = Field(default_factory=list, description="Dimensions already covered by Recommender, e.g. ['destination', 'accommodation']")


class TraceLog(BaseModel):
    """单节点执行审计记录（可观测性）。"""
    node: str = Field(..., description="Node name")
    status: str = Field(..., description="Execution status: SUCCESS / FAIL / REJECTED / SKIPPED")
    detail: Dict[str, Any] = Field(default_factory=dict, description="Key execution details")
    latency_ms: int = Field(default=0, description="Total wall time including LLM call (ms)")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage breakdown")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 completion timestamp"
    )

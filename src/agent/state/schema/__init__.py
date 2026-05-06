"""Agent 2.0 State Schema — 按领域拆分为 5 个子模块。

向后兼容：所有模型从本包顶层重导出，from src.agent.state.schema import X 保持不变。
"""

from .control import RouteMetadata, ExecutionSigns, TraceLog
from .domain import UserProfile, SearchTask, RetrievalMetadata
from .delivery import (
    UserSelections,
    RecommendationItem,
    RecommenderOutput,
    Activity,
    DayPlan,
    PlannerOutput,
)
from .research import (
    ResearchResult,
    CriticResult,
    LoopSummary,
    ResearchLoopInternal,
    ResearchManifest,
)
from .llm_contracts import (
    GatewayOutput,
    AnalystOutput,
    ManagerOutput,
    QueryGeneratorOutput,
)

__all__ = [
    # control
    "RouteMetadata",
    "ExecutionSigns",
    "TraceLog",
    # domain
    "UserProfile",
    "SearchTask",
    "RetrievalMetadata",
    # delivery
    "UserSelections",
    "RecommendationItem",
    "RecommenderOutput",
    "Activity",
    "DayPlan",
    "PlannerOutput",
    # research
    "ResearchResult",
    "CriticResult",
    "LoopSummary",
    "ResearchLoopInternal",
    "ResearchManifest",
    # llm_contracts
    "GatewayOutput",
    "AnalystOutput",
    "ManagerOutput",
    "QueryGeneratorOutput",
]

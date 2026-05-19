"""Research Loop 子图私有状态 — 仅包含 4 个内部节点实际访问的字段。

父图专属字段（plan_data, recommendation_data, route_metadata, execution_signs,
needs_exit, planned_dimensions 等）不可访问，由 LangGraph 在子图边界自动过滤。
"""

from operator import add
from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from src.agent.state.schema import ResearchManifest, TraceLog, UserProfile
from src.agent.state.state import _merge_research_manifest


class ResearchLoopState(TypedDict):
    """Research Loop 子图内部状态。

    LangGraph 在父图调用子图时自动将 TravelState 过滤为此 schema，
    内部节点无法访问父图专属字段。
    """
    research_data: Annotated[ResearchManifest, _merge_research_manifest]
    focus_dimension: Optional[str]
    dimension_hints: Dict[str, str]
    user_profile: Annotated[Optional[UserProfile], lambda left, right: right if right is not None else left]
    messages: List[BaseMessage]
    trace_history: Annotated[List[TraceLog], add]

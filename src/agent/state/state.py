"""
Module: src.agent.state
Responsibility: Defines the typed dictionaries for LangGraph state management in Agent 2.0.
Parent Module: src.agent
Dependencies: typing, langgraph, src.agent.schema

This module serves as the global blueprint (State) for the agent. It strictly follows
the decoupling principle: raw data is stored externally, while this state carries
references, metadata, and control flags.
"""

from operator import add
from typing import Annotated, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from src.agent.state.schema import (
    UserProfile, ResearchManifest, RouteMetadata, TraceLog,
    ExecutionSigns, RecommenderOutput, PlannerOutput, UserSelections,
)

class TravelState(TypedDict):
    """
    Agent 2.0 Global Blackboard State.

    字段权限: 每个字段有且仅有一个写入节点。读取权限见 STATE_SPEC.md。
    """

    # ── 对话上下文 ─────────────────────────────────────────
    messages: Annotated[List[BaseMessage], add_messages]

    # ── 业务数据 (Analyst 写入) ────────────────────────────
    user_profile: UserProfile

    # ── 调研状态 (Research Loop 写入, Manager reset) ───────
    research_data: ResearchManifest

    # ── 交付数据 ──────────────────────────────────────────
    recommendation_data: Optional[Dict[str, RecommenderOutput]]
    plan_data: Optional[PlannerOutput]

    # ── 用户交互 (Manager 写入) ────────────────────────────
    user_selections: Optional[UserSelections]

    # ── 控制面 ────────────────────────────────────────────
    route_metadata: RouteMetadata
    execution_signs: ExecutionSigns

    # ── 可观测性 ──────────────────────────────────────────
    trace_history: Annotated[List[TraceLog], add]

    # ── 终止信号 (Gateway 写入) ────────────────────────────
    needs_exit: bool

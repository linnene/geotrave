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
    ExecutionSigns, RecommenderOutput, PlannerOutput,
)
from src.agent.state.schema.research import ResearchLoopInternal


def _merge_research_manifest(left: Optional[ResearchManifest], right: Optional[ResearchManifest]) -> ResearchManifest:
    """并行 research_loop 分支的结果合并 reducer。

    Annotated reducer 在 LangGraph 中每次写入都触发（不仅并行合并），因此必须
    保留 right.loop_state 而非重置，否则子图内部的 QG→Search→Critic 循环状态丢失。
    - research_hashes: dict 合并
    - research_history: 拼接去重
    - matched_doc_ids: 拼接去重
    - loop_state: 保留最新写入（子图内部状态由各节点自行管理）
    """
    if left is None:
        return right
    if right is None:
        return left
    merged_hashes = {**left.research_hashes, **right.research_hashes}
    merged_history = list(dict.fromkeys(left.research_history + right.research_history))
    merged_doc_ids = list(set(left.matched_doc_ids + right.matched_doc_ids))
    return ResearchManifest(
        research_hashes=merged_hashes,
        research_history=merged_history,
        matched_doc_ids=merged_doc_ids,
        loop_state=right.loop_state,
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
    research_data: Annotated[ResearchManifest, _merge_research_manifest]

    # ── 维度控制 (DimensionPlanner 写入, Send 扇出消费) ────
    planned_dimensions: List[str]
    dimension_hints: Annotated[Dict[str, str], lambda left, right: {**left, **right}]
    focus_dimension: Annotated[Optional[str], lambda left, right: right if right is not None else left]

    # ── 交付数据 ──────────────────────────────────────────
    recommendation_data: Optional[Dict[str, RecommenderOutput]]
    plan_data: Optional[PlannerOutput]

    # ── 控制面 ────────────────────────────────────────────
    route_metadata: RouteMetadata
    execution_signs: ExecutionSigns

    # ── 可观测性 ──────────────────────────────────────────
    trace_history: Annotated[List[TraceLog], add]

    # ── 终止信号 (Gateway 写入) ────────────────────────────
    needs_exit: bool

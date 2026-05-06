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

    LangGraph Send 扇出后多个分支并发写入 research_data 时触发。
    - research_hashes: dict 合并（并行分支产出的 query key 不冲突）
    - research_history: 拼接去重（保持插入顺序）
    - matched_doc_ids: 拼接去重
    - loop_state: 重置（合并后不再需要内部循环状态）
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
        loop_state=ResearchLoopInternal(),
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
    dimension_hints: Dict[str, str]
    focus_dimension: Optional[str]

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

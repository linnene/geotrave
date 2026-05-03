"""
Module: src.agent.state.schema
Responsibility: Pydantic models for Agent 2.0 shared state, LLM output parsing,
                and Research Loop internal communication.
Parent Module: src.agent.state
Dependencies: pydantic, typing, datetime

All Field descriptions use English for open-source readiness.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


# ==============================================================================
# 图控制与审计 — 路由信号与可观测性
# ==============================================================================


class RouteMetadata(BaseModel):
    """控制面路由指令，仅由 Manager 写入。

    is_error 已废弃，Manager 重构后将移除。下游节点和条件边均不读取此字段。
    """
    next_node: str = Field(..., description="Target node name for the next hop")
    reason: str = Field(..., description="Rationale behind the routing decision")
    is_error: bool = Field(default=False, description="[DEPRECATED] Always False, never checked")


class ExecutionSigns(BaseModel):
    """跨节点信号面 — 各业务节点设置的布尔标记。

    is_loop_exit 由 Hash 节点在子图退出时设置；目前已预留，尚未被条件边消费。
    """
    is_safe: bool = Field(default=True, description="Gateway: input passed safety check")
    is_core_complete: bool = Field(default=False, description="Analyst: core profile fields sufficient")
    is_loop_exit: bool = Field(default=False, description="Hash: research loop exited cleanly")
    is_recommendation_complete: bool = Field(default=False, description="Recommender: destination/accommodation/dining recommendations generated")
    is_plan_complete: bool = Field(default=False, description="Planner: day-by-day itinerary generated")
    is_selection_made: bool = Field(default=False, description="Manager: user has made selections from recommendations (or explicitly delegated to agent)")
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


# ==============================================================================
# 业务领域 — 结构化用户画像与搜索任务定义
# ==============================================================================


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
    # 例如: {"quiet_destination_preference": "人少", "near_sea": True}
    Flex: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Overflow for unstructured preferences not covered by named fields"
    )

    # ------------------------------------------------------------------
    # Core-UserProfile 完备性审计
    # ------------------------------------------------------------------

    def check_completeness(self) -> tuple[bool, List[str]]:
        """审计画像完备性。

        返回:
            (is_core_complete, all_missing_fields)

        核心字段决定是否可启动调研:
            destination, days/date, people_count, budget_limit。
        完整缺失字段列表供 Reply 节点引导用户补充信息。
        """
        # 1. 核心字段 — 决定是否可启动调研
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

        # 2. 全部字段 — 供 Reply 节点引导追问
        all_missing: List[str] = []
        for field_name in self.model_fields.keys():
            if field_name == "Flex":
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
    dimension: Literal[
        "transportation", "accommodation", "dining", "attraction",
        "general", "weather", "policy"
    ] = Field(..., description="Research dimension this task addresses")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=("Tool-specific arguments. ")
    )
    rationale: str = Field(..., description="Why this task was generated and what it should yield -- [ Later well be drop only works in DEBUG]")


class RetrievalMetadata(BaseModel):
    """工具 handler 返回的原始检索结果信封。

    Search 节点读取 payload 字段后包裹为 ResearchResult 送入 Critic，
    不再直接暴露给父图。hash_key 仅用于工具内部追踪。
    """
    hash_key: str = Field(..., description="Content-addressable key for KV store lookup")
    source: str = Field(..., description="Data source label or URL")
    relevance_score: float = Field(default=0.0, description="Critic-assigned relevance score")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Full result payload")


# ==============================================================================
# LLM 输出 Schema — 每个 LLM 驱动节点的 JSON 解析契约
# ==============================================================================


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
    user_request: str = Field(
        ...,
        description="Summarised core intent derived from conversation, e.g. 'User wants小众 spots in Dali in May'"
    )
    reason: str = Field(..., description="Brief explanation of extraction and merge logic")


class UserSelections(BaseModel):
    """用户在推荐列表中的选择结果。Manager 从用户消息中提取，Planner 遵守。

    当用户明确说"随便/都行/你定"时，对应字段设为 "agent_choice"，
    Planner 可自由从推荐中挑选最优项。
    """
    chosen_destination: Optional[str] = Field(
        default=None,
        description="Picked destination name, or 'agent_choice' when user delegates to agent"
    )
    chosen_accommodation: Optional[str] = Field(
        default=None,
        description="Picked accommodation name, or 'agent_choice' when user delegates to agent"
    )
    chosen_dining: Optional[str] = Field(
        default=None,
        description="Picked dining name, or 'agent_choice' when user delegates to agent"
    )
    needs_reselect: bool = Field(
        default=False,
        description="User rejected current batch and wants re-recommendation"
    )
    reselection_feedback: Optional[str] = Field(
        default=None,
        description="User's revised requirements when requesting re-recommendation"
    )


class ManagerOutput(BaseModel):
    """Manager 节点结构化输出 — 控制全局路由。"""
    next_stage: Literal["research_loop", "recommender", "planner", "reply"] = Field(
        ...,
        description=(
            "Next routing target. research_loop: execute research subgraph (QG→Search→Critic⇄QG|Hash); "
            "recommender: recommend items; planner: generate itinerary; reply: respond to user"
        )
    )
    rationale: str = Field(..., description="Detailed logic behind this routing decision")
    user_selections: Optional[UserSelections] = Field(
        default=None,
        description="Extracted user selections when user responds to recommendation list"
    )


class QueryGeneratorOutput(BaseModel):
    """QueryGenerator 节点结构化输出。"""
    tasks: List[SearchTask] = Field(..., description="Decomposed multi-dimension search task list")
    research_strategy: str = Field(
        ...,
        description="Overall research strategy narrative, e.g. '先通过通用搜索确定热门商圈，再针对性检索高评分民宿'"
    )


# ==============================================================================
# Research Loop 模型 — 子图内部通信
# ==============================================================================


class ResearchResult(BaseModel):
    """统一信封，包裹每条工具结果后送入 Critic。

    不同工具返回异构形状（POI JSON、网页文本、爬虫输出），此信封将其归一化，
    使得 Critic 和 Hash 仅依赖本契约，不依赖具体工具的 schema。
    """
    tool_name: str = Field(..., description="Tool that produced this result")
    query: str = Field(..., description="Original query text or serialised parameters")
    content_type: Literal["json", "text", "html", "url_list"] = Field(
        ..., description="Shape of the content field"
    )
    content: Any = Field(..., description="Full original result (shape governed by content_type)")
    content_summary: str = Field(
        ...,
        description="Short summary (≤500 chars) for Critic LLM scoring; avoids token blow-up on long text"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 creation time"
    )


class CriticResult(BaseModel):
    """Critic Layer 2 (LLM) 在 Layer 1 (黑名单) 通后产出的单条评估结过果。"""
    query: str = Field(..., description="Query text this evaluation corresponds to")
    tool_name: str = Field(
        default="",
        description="Tool that produced this result; echoed from ResearchResult, used by Hash to separate doc vs non-doc"
    )
    safety_tag: Literal["safe", "unsafe"] = Field(
        ..., description="Content safety verdict"
    )
    relevance_score: float = Field(
        ..., ge=0, le=100, description="How well the result answers the query"
    )
    utility_score: float = Field(
        ..., ge=0, le=100, description="How actionable the result is for travel planning"
    )
    rationale: str = Field(..., description="Scoring rationale in natural language")


class LoopSummary(BaseModel):
    """单轮 Research Loop 迭代的聚合统计。"""
    pass_count: int = Field(..., description="Number of results passing all three filter layers")
    total_count: int = Field(..., description="Total results evaluated this iteration")
    avg_relevance: float = Field(..., description="Mean relevance score across passed results")
    avg_utility: float = Field(..., description="Mean utility score across passed results")
    dimensions_covered: List[str] = Field(
        default_factory=list,
        description="Research dimensions covered by passed results"
    )


class ResearchLoopInternal(BaseModel):
    """子图私有状态。仅 Research Loop 节点读写这些字段。

    嵌套在 ResearchManifest.loop_state 中，父图只看到一个 key。
    外部节点（Manager、Reply、Recommender、Planner）严禁直接读写。
    """
    # --- QueryGenerator 输出（QG 写入，Search 读取并清空）---
    active_queries: List[SearchTask] = Field(
        default_factory=list,
        description="Search tasks generated by QG; Search node consumes then clears them"
    )

    # --- Search 输出（Search 写入，Critic 读取）---
    query_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="{{query_text: ResearchResult}} key-value pairs from the current iteration"
    )

    # --- Critic 输出（Critic 写入，Hash 和下一轮 QG 读取）---
    passed_results: List[CriticResult] = Field(
        default_factory=list, description="Results passing this iteration's filter"
    )
    all_passed_results: List[CriticResult] = Field(
        default_factory=list, description="Cumulative passed results across all iterations"
    )
    passed_queries: List[str] = Field(
        default_factory=list,
        description="Query texts that have already passed; QG must deduplicate against these"
    )
    feedback: Optional[str] = Field(
        default=None, description="Critic feedback for the next QueryGenerator iteration"
    )
    continue_loop: bool = Field(
        default=True, description="Critic decision: should the loop keep iterating?"
    )
    loop_iteration: int = Field(default=0, description="Current loop iteration count (0-indexed)")
    loop_summary: Optional[LoopSummary] = Field(
        default=None, description="Aggregated stats for the most recent iteration"
    )

    # --- 文档检索结果（Search 直接写入，不经过 Critic/Hash，跨迭代累积）---
    passed_doc_ids: List[str] = Field(
        default_factory=list,
        description="Document IDs accumulated across iterations; Search writes directly, Hash promotes to Manifest"
    )


# ==============================================================================
# Research Manifest — 父图可见的研究状态视图
# ==============================================================================


class ResearchManifest(BaseModel):
    """存储在 TravelState.research_data 中的顶层研究状态模型。

    外部契约（Manager、Reply、Recommender、Planner 读取）:
        research_hashes  — {query: [hash_key, ...]} 映射
        research_history — 有序的 user_request 字符串列表

    内部契约（仅 Research Loop 子图节点读写）:
        loop_state       — ResearchLoopInternal（详见该类，含 active_queries 等子图私有字段）
    """
    research_hashes: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="{{query_text: [hash_key, ...]}} — minimal global-state exposure"
    )
    loop_state: ResearchLoopInternal = Field(
        default_factory=ResearchLoopInternal,
        description="Subgraph-private state; external nodes must NOT touch"
    )
    research_history: List[str] = Field(
        default_factory=list,
        description="Ordered list of user_request strings; Manager uses last entry for freshness checks"
    )
    matched_doc_ids: List[str] = Field(
        default_factory=list,
        description="Document IDs matched this research session; stored in retrieval_db, separate from research_hashes"
    )


# ==============================================================================
# Recommender / Planner 输出 Schema — LLM 驱动的交付节点
# ==============================================================================


class RecommendationItem(BaseModel):
    """单条推荐项 — 前端渲染用。

    每个推荐项包含名称、特点、推荐原因和五星制评分。
    rating 支持半星（如 4.5），范围 1.0–5.0。
    """
    name: str = Field(..., description="推荐项名称（目的地/酒店/餐厅名）")
    features: str = Field(..., description="推荐项特点/亮点，如'交通便利，步行到地铁站3分钟'")
    reason: str = Field(..., description="推荐原因，基于研究数据和用户偏好")
    rating: float = Field(..., ge=1.0, le=5.0, description="推荐指数 1-5 星，支持半星如 4.5")


class RecommenderOutput(BaseModel):
    """Recommender 节点结构化输出 — 每次调用仅输出一个维度。"""
    dimension: Literal["destination", "accommodation", "dining"] = Field(
        ..., description="本轮推荐维度"
    )
    items: List[RecommendationItem] = Field(
        default_factory=list, description="该维度的推荐列表（1-3 项）"
    )
    strategy: str = Field(default="", description="推荐策略简述")
    tip: str = Field(default="", description="引导用户下一步的提示，如'选定目的地后我帮您挑住宿'")


class Activity(BaseModel):
    """单日活动中的一项活动。"""
    time: str = Field(..., description="Time slot, e.g. '09:00-11:30'")
    place: str = Field(..., description="Attraction / restaurant / transport node name")
    type: Literal["attraction", "dining", "transport", "rest", "accommodation"] = Field(
        ..., description="Activity type"
    )
    description: str = Field(..., description="What to do / what to expect")
    duration_min: int = Field(..., ge=0, description="Estimated duration in minutes")
    transport: Optional[str] = Field(default=None, description="Transport method between this and next activity")


class DayPlan(BaseModel):
    """单日行程安排。"""
    day: int = Field(..., ge=1, description="Day number (1-indexed)")
    date: Optional[str] = Field(default=None, description="ISO date string if known")
    activities: List[Activity] = Field(default_factory=list, description="Activities for this day")


class PlannerOutput(BaseModel):
    """Planner 节点结构化输出。"""
    days: List[DayPlan] = Field(default_factory=list, description="Day-by-day itinerary")
    total_budget_estimate: Optional[str] = Field(
        default=None, description="Estimated total cost summary"
    )
    notes: List[str] = Field(
        default_factory=list, description="Notes, caveats, alternative plans (e.g. rainy day backup)"
    )

"""
Module: src.agent.schema
Responsibility: Defines all Pydantic models for structured data and Agent 2.0 communication.
Parent Module: src.agent
Dependencies: pydantic, typing, datetime
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# ==============================================================================
# Graph Control & Audit Models
# ==============================================================================

class RouteMetadata(BaseModel):
    """
    用于控制图流转的元数据 (Control Plane)
    权限控制：仅允许 Manager (作为 Router) 进行修改。
    """
    next_node: str = Field(..., description="下一跳节点名称")
    reason: str = Field(..., description="流转决策的原因/依据")
    is_error: bool = Field(default=False, description="是否发生了需要特殊处理的异常")

class ExecutionSigns(BaseModel):
    """
    统一信号面板 (Signal Plane)
    用于存放各业务节点产生的、影响流转逻辑的状态位。
    """
    is_safe: bool = Field(default=True, description="Gateway 查验结果：是否放行")
    is_core_complete: bool = Field(default=False, description="Analyst 审计结果：核心信息是否完整")
    is_loop_exit: bool = Field(default=False, description="Critic 审计结果：是否跳出研究循环")

class TraceLog(BaseModel):
    """节点执行的详细审计记录 (Observability)"""
    node: str = Field(..., description="节点名称")
    status: str = Field(..., description="执行状态: SUCCESS, FAIL, REJECTED, SKIPPED")
    detail: Dict[str, Any] = Field(default_factory=dict, description="节点执行的关键详情摘要")
    latency_ms: int = Field(default=0, description="代码+LLM调用总耗时(ms)")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token消耗情况")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="运行完成的时间戳")

# ==============================================================================
# Business Data Models
# ==============================================================================

class UserProfile(BaseModel):
    """结构化的用户旅行偏好与约束 (Business Context)"""
    destination: List[str] = Field(default_factory=list, description="目的地列表")
    days: Optional[int] = Field(None, description="旅行天数")
    date: Optional[List[str]] = Field(None, description="日期范围 [开始, 结束]")
    people_count: Optional[int] = Field(1, description="出行人数")
    budget_limit: Optional[int] = Field(0, description="总预算上限")
    
    accommodation: Optional[str] = Field(None, description="住宿偏好")
    dining: Optional[str] = Field(None, description="餐饮禁忌或偏好")
    transportation: Optional[str] = Field(None, description="交通工具偏好")
    pace: Optional[str] = Field(None, description="旅行节奏 (如: 休闲, 特种兵)")

    Flex: Optional[Dict[str, Any]] = Field(default_factory=dict, description="灵活字段，用于存储额外的用户信息或偏好，一些用户明显提及并，且没有被字段规定的信息")

    def check_completeness(self) -> tuple[bool, List[str]]:
        """
        判断字段填写情况。
        返回: (是否满足开启搜索的核心条件, 仍缺失的所有字段列表)
        核心字段(用于控制流转): destination, days/date, people_count, budget_limit
        所有字段(用于传输给 Reply): UserProfile 类定义的所有字段
        """
        # 1. 核心字段校验 (决定是否唤醒 Manager)
        core_missing = []
        if not self.destination: core_missing.append("destination")
        if not (self.days ): core_missing.append("days")
        if not (self.date): core_missing.append("date")
        if not self.people_count: core_missing.append("people_count")
        if self.budget_limit is None: core_missing.append("budget_limit")
        
        if len(core_missing) > 0:
            is_core_complete = False
        else:
            is_core_complete = True

        # 2. 扫描所有字段 (用于 Reply 引导)
        all_missing = []
        # 获取 UserProfile 定义的所有字段名 (排除 Flex 和方法)
        for field_name in self.model_fields.keys():
            if field_name == "Flex": continue
            val = getattr(self, field_name)
            if val is None or val == "" or val == [] or val == 0:
                all_missing.append(field_name)
                
        return is_core_complete, all_missing

class RetrievalMetadata(BaseModel):
    """外部存储数据的索引模型"""
    hash_key: str = Field(..., description="异步 KV 库中的存储键 (Content Hash)")
    source: str = Field(..., description="数据来源标题或链接")
    relevance_score: float = Field(default=0.0, description="Critic 打出的相关性评分")
    payload: Dict[str, Any] = Field(default_factory=dict, description="检索结果的完整数据载荷")

class SearchTask(BaseModel):
    """具体的搜索任务定义，支持动态参数"""
    tool_name: str = Field(..., description="拟调用的工具名称（如 spatial_search, route_search）")
    dimension: Literal["transportation", "accommodation", "dining", "attraction", "general", "weather", "policy"] = Field(..., description="搜索维度")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="针对该工具的具体调用参数。spatial_search 需 center/radius_m/category/limit；route_search 需 origin/destination/mode"
    )
    rationale: str = Field(..., description="生成该任务的原因，以及期望获取的信息点内容")

class QueryGeneratorOutput(BaseModel):
    """Pydantic model for QueryGenerator node output"""
    tasks: List[SearchTask] = Field(..., description="拆解后的多维度搜索任务列表")
    research_strategy: str = Field(..., description="整体的研究策略描述。例如：'先通过通用搜索确定热门商圈，再针对性检索高评分民宿'。")
    focus_areas: List[str] = Field(..., description="本次研究需要重点突破的信息盲区")

class ResearchManifest(BaseModel):
    """检索循环的状态看板 (Research Loop Context)"""
    active_queries: List[SearchTask] = Field(default_factory=list, description="当前循环待执行的查询任务列表，由 QueryGenerator 节点生成")
    verified_results: List[RetrievalMetadata] = Field(default_factory=list, description="已通过 Critic 验证的结果索引")
    feedback_history: List[str] = Field(default_factory=list, description="Critic 给出的打回反馈原因Log")
    research_history: List[str] = Field(default_factory=list, description="每轮研究的 user_request 记录，用于 Manager 判断已有结果是否属于当前诉求轮次")

# ==============================================================================
# ManagerOutput Output Schema
# ==============================================================================

class ManagerOutput(BaseModel):
    """Manager 节点的结构化输出，用于控制全局路由"""
    next_stage: Literal["analyst","query_generator", "recommender", "planner", "reply"] = Field(
        ..., 
        description="下一阶段的路由目标。analyst: 专用的需求分析节点; query_generator: 启动/继续搜索; recommender: 进行项目推荐; planner: 生成最终计划; reply: 直接回复用户"
    )
    rationale: str = Field(..., description="做出此路由决策的详细逻辑依据")
    priority_notes: Optional[str] = Field(None, description="下一阶段节点的执行重点")

# ==============================================================================
# GatewayOutput Output Schema
# ==============================================================================

class GatewayOutput(BaseModel):
    """Pydantic model for strict LLM output validation"""
    is_valid: bool = Field(description="是否是一个有效且合规的指令")
    category: Literal["legal", "malicious", "chitchat"] = Field(description="请求的具体分类")
    reason: str = Field(description="做出此判断的简短理由或摘要")
    reply: str = Field(default="", description="如果无效时的回复语；如果合法且涉及PII，此字段应包含脱敏后的文本（若定义要求覆盖输入），否则保持为空。")
    sanitized_text: Optional[str] = Field(default=None, description="如果检测到 PII 信息，请返回脱敏后的用户输入文本；若无敏感信息，保持为 None。")

# ==============================================================================
# AnalystOutput Output Schema
# ==============================================================================

class AnalystOutput(BaseModel):
    """Pydantic model for Analyst node output"""
    updated_profile: UserProfile = Field(..., description="经过合并与更新后的完整 UserProfile 对象")
    missing_fields: List[str] = Field(default_factory=list, description="UserProfile中仍缺失的字段列表")
    user_request: str = Field(..., description="基于对话历史总结的当前任务核心诉求。例如：'用户想知道5月份去大理有哪些小众景点'。此字段将作为后续 Planner 节点的直接输入。")
    reason: str = Field(description="本次提取与合并逻辑的简要说明")

# ==============================================================================
# QueryGenerator Output Schema (continued from above)
# ==============================================================================
# SearchTask, QueryGeneratorOutput are defined earlier


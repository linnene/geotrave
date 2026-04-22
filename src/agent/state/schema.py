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
    """用于控制图流转的元数据 (Control Plane)"""
    next_node: str = Field(..., description="下一跳节点名称")
    reason: str = Field(..., description="流转决策的原因/依据")
    is_error: bool = Field(default=False, description="是否发生了需要特殊处理的异常")

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

class RetrievalMetadata(BaseModel):
    """外部存储数据的索引模型"""
    hash_key: str = Field(..., description="异步 KV 库中的存储键 (Content Hash)")
    source: str = Field(..., description="数据来源标题或链接")
    relevance_score: float = Field(default=0.0, description="Critic 打出的相关性评分")

class ResearchManifest(BaseModel):
    """检索循环的状态看板 (Research Loop Context)"""
    active_queries: List[str] = Field(default_factory=list, description="当前循环待执行的查询列表")
    verified_results: List[RetrievalMetadata] = Field(default_factory=list, description="已通过 Critic 验证的结果索引")
    feedback_history: List[str] = Field(default_factory=list, description="Critic 给出的打回反馈原因Log")



# ==============================================================================
# GatewayOutput Output Schema
# ==============================================================================

class GatewayOutput(BaseModel):
    """Pydantic model for strict LLM output validation"""
    is_valid: bool = Field(description="是否是一个有效且合规的指令")
    category: Literal["legal", "malicious", "chitchat"] = Field(description="请求的具体分类")
    reason: str = Field(description="做出此判断的简短理由或摘要")
    reply: str = Field(default="", description="如果无效，生成给用户的礼貌性推脱回复；如果合法，保持为空字符串。")

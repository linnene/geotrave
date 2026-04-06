from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from typing import Annotated, TypedDict, List, Dict, Optional
from pydantic import BaseModel, Field

# ----------------- Con Modle -----------------

class HardConstraints(BaseModel):
    """硬约束集合：具有一票否决权的信息"""
    budget_limit: Optional[int] = Field(None, description="预算绝对上限")
    max_walk_km: Optional[float] = Field(None, description="每日最大步行距离（km）")
    visa_restrictions: List[str] = Field(default_factory=list, description="签证或证件限制")
    allergies: List[str] = Field(default_factory=list, description="明确的过敏史（如：花生、海鲜）")
    locked_resources: List[Dict] = Field(default_factory=list, description="已锁定的机票/酒店时间和地点")

class SoftPreferences(BaseModel):
    """软偏好集合：用于加权评分的信息"""
    travel_pace: Optional[str] = Field(None, description="旅行节奏（紧凑、适中、休闲）")
    interests: List[str] = Field(default_factory=list, description="偏好主题（历史人文、自然风光等）")
    dietary_pref: List[str] = Field(default_factory=list, description="餐饮偏好（当地特色、街头小吃等）")
    accommodation_type: List[str] = Field(default_factory=list, description="住宿偏好（民宿、酒店、青旅）")

# ----------------- Con Modle -----------------

# ----------------- Shared State -----------------

class TravelState(TypedDict):
    """全局状态白板"""
    messages: Annotated[list[BaseMessage], add_messages] # 历史对话

    # 核心目标
    destination: str | None # 目的地
    days: int | None        # 游玩天数
    date: list[str] | None  # 日期范围 [开始, 结束]
    people: list[str] | None # 旅客构成:「"老人一位"、"儿童两位"、"一对情侣"」

    # 约束与偏好重构
    hard_constraints: HardConstraints
    soft_preferences: SoftPreferences

    # 过程变量
    tags: list[str] | None  # 自动识别的增强标签
    retrieval_context: str | None # 研究员节点提供的检索上下文

# ----------------- Shared State -----------------

# ----------------- Analyzer node -----------------

class TravelInfo(BaseModel):
    """分析师输出的结构化数据"""
    destination: Optional[str] = Field(None, description="目的地")
    days: Optional[int] = Field(None, description="天数")
    date: Optional[List[Optional[str]]] = Field(None, min_length=2, max_length=2, description="日期范围")
    people_count: int = Field(default=1, description="总人数")
    
    # 映射到硬约束
    hard_constraints: HardConstraints = Field(default_factory=HardConstraints)
    # 映射到软偏好
    soft_preferences: SoftPreferences = Field(default_factory=SoftPreferences)
    
    tags: List[str] = Field(default_factory=list, description="风格标签")
    reply: str = Field(description="话术回复（追问或分析结果）")

# ----------------- Analyzer node -----------------

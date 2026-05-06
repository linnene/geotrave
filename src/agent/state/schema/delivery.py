"""交付层模型 — 推荐、选择、行程规划。"""

from typing import List, Optional
from pydantic import BaseModel, Field
from typing import Literal


class RecommendationItem(BaseModel):
    """单条推荐项 — 前端渲染用。

    每个推荐项包含名称、特点、推荐原因和五星制评分。
    rating 支持半星（如 4.5），范围 1.0–5.0。
    """
    name: str = Field(..., description="推荐项名称（目的地/酒店/餐厅名）")
    features: str = Field(..., description="推荐项特点/亮点，如'交通便利，步行到地铁站3分钟'")
    reason: str = Field(default="基于研究数据匹配", description="推荐原因，基于研究数据和用户偏好")
    rating: float = Field(..., ge=1.0, le=5.0, description="推荐指数 1-5 星，支持半星如 4.5")


class RecommenderOutput(BaseModel):
    """Recommender 节点结构化输出 — 每次调用仅输出一个维度。"""
    dimension: str = Field(
        ..., description="本轮推荐维度（自由维度，如 'destination' / 'accommodation' / 'dining' / 'shopping' / 'attraction' 等）"
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

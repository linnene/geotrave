from typing import List, Optional
from pydantic import BaseModel, Field

# ----------------- Analyzer node -----------------

class UserProfile(BaseModel):
    """扁平化的用户旅游需求和偏好画像"""
    destination: List[str] = Field(default_factory=list, description="目的地列表(支持多个)")
    days: Optional[int] = Field(None, description="天数")
    date: Optional[List[Optional[str]]] = Field(None, min_length=2, max_length=2)
    people_count: Optional[int] = Field(default=1)
    budget_limit: Optional[int] = Field(default=0)
    
    accommodation: Optional[str] = Field(description="住宿偏好（例如：五星级、民宿、青旅）")
    dining: Optional[str] = Field(description="餐饮偏好或禁忌（例如：海鲜、素食、不吃辣）")
    transportation: Optional[str] = Field(description="交通偏好（例如：高铁、自驾、房车）")
    pace: Optional[str] = Field(description="游玩节奏（例如：休闲、特种兵、深度游）")
    activities: List[str] = Field(default_factory=list, description="用户明确想体验的具体活动或主题（例如：逛博物馆、看海、购物等）")
    
    preferences: List[str] = Field(default_factory=list, description="用户随口一提的任何未结构化分类的正面兴趣、偏好希望体验的事项（例如：有小猫小狗最好、顺便看夜景）")
    avoidances: List[str] = Field(default_factory=list, description="用户无论软性或硬性，明确表示不想要/避雷/讨厌的负面选项（例如：不去爬山、不要全聚德、绝对不能吃海鲜）")

class TravelInfo(BaseModel):
    """分析师输出的整个结构化数据"""
    user_profile: UserProfile = Field(default_factory=lambda: UserProfile())
    needs_research: bool = Field(default=False, description="是否需要主动唤起检索节点（比如核心需求刚凑全、或者发生了关键变更使得旧信息不再适用时设为True）")
    reply: str = Field(description="追问User")

# ----------------- Researcher node -----------------

class ResearchPlan(BaseModel):
    """研究员生成的检索计划"""
    local_query: Optional[str] = Field(description="知识库检索关键词")
    web_queries: List[str] = Field(default_factory=list, description="在线搜索关键词")
    need_weather: bool = Field(default=False, description="是否需要查询目的地的天气预报")
    need_api: List[str] = Field(default_factory=list)
"""
Module: src.utils.llm_factory
Responsibility: Centralized factory for creating and configuring LLM instances.
"""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from src.utils.config import (
    GLOBAL_MODEL_API_KEY,
    GLOBAL_MODEL_BASE_URL,
    GLOBAL_MODEL_ID,

    GATEWAY_MODEL_API_KEY,
    GATEWAY_MODEL_BASE_URL,
    GATEWAY_MODEL_ID,
    ANALYST_MODEL_API_KEY,
    ANALYST_MODEL_BASE_URL,
    ANALYST_MODEL_ID,

    RESEARCHER_MODEL_API_KEY,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_ID,

    PLANNER_MODEL_API_KEY,
    PLANNER_MODEL_BASE_URL,
    PLANNER_MODEL_ID,

    RECOMMENDER_MODEL_API_KEY,
    RECOMMENDER_MODEL_BASE_URL,
    RECOMMENDER_MODEL_ID,

    CRITIC_MODEL_API_KEY,
    CRITIC_MODEL_BASE_URL,
    CRITIC_MODEL_ID,

    MANAGER_MODEL_API_KEY,
    MANAGER_MODEL_BASE_URL,
    MANAGER_MODEL_ID,

    DIMENSION_PLANNER_MODEL_API_KEY,
    DIMENSION_PLANNER_MODEL_BASE_URL,
    DIMENSION_PLANNER_MODEL_ID,

    REPLY_MODEL_API_KEY,
    REPLY_MODEL_BASE_URL,
    REPLY_MODEL_ID,
)

_NODE_CONFIG: dict[str, tuple[str, str, str]] = {
    "Gateway":          (GATEWAY_MODEL_API_KEY,           GATEWAY_MODEL_BASE_URL,           GATEWAY_MODEL_ID),
    "Analyst":          (ANALYST_MODEL_API_KEY,           ANALYST_MODEL_BASE_URL,           ANALYST_MODEL_ID),
    "QueryGenerator":   (RESEARCHER_MODEL_API_KEY,        RESEARCHER_MODEL_BASE_URL,        RESEARCHER_MODEL_ID),
    "Manager":          (MANAGER_MODEL_API_KEY,           MANAGER_MODEL_BASE_URL,           MANAGER_MODEL_ID),
    "Reply":            (REPLY_MODEL_API_KEY,             REPLY_MODEL_BASE_URL,             REPLY_MODEL_ID),
    "Recommender":      (RECOMMENDER_MODEL_API_KEY,       RECOMMENDER_MODEL_BASE_URL,       RECOMMENDER_MODEL_ID),
    "Planner":          (PLANNER_MODEL_API_KEY,           PLANNER_MODEL_BASE_URL,           PLANNER_MODEL_ID),
    "Critic":           (CRITIC_MODEL_API_KEY,            CRITIC_MODEL_BASE_URL,            CRITIC_MODEL_ID),
    "DimensionPlanner": (DIMENSION_PLANNER_MODEL_API_KEY, DIMENSION_PLANNER_MODEL_BASE_URL, DIMENSION_PLANNER_MODEL_ID),
}


class LLMFactory:
    """LLM 实例工厂，支持按节点名称获取定制配置的 LLM。"""

    @staticmethod
    def get_model(node_name: str, temperature: float = 0, streaming: bool = False, max_tokens: int | None = None):
        """根据节点名称返回对应的 ChatOpenAI 实例。"""
        node_cfg = _NODE_CONFIG.get(node_name)
        if node_cfg is not None:
            api_key, base_url, model = node_cfg
        else:
            api_key, base_url, model = GLOBAL_MODEL_API_KEY, GLOBAL_MODEL_BASE_URL, GLOBAL_MODEL_ID

        return ChatOpenAI(
            api_key=SecretStr(api_key) if api_key else None,
            base_url=base_url,
            model=model,
            temperature=temperature,
            streaming=streaming,
        )
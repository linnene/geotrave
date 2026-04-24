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
    RESEARCHER_MODEL_ID
)

class LLMFactory:
    """
    LLM 实例工厂，支持按节点名称获取定制配置的 LLM。
    """
    
    @staticmethod
    def get_model(node_name: str, temperature: float = 0, streaming: bool = False, max_tokens: int = None):
        """
        根据节点名称返回对应的 ChatOpenAI 实例。
        """
        # 默认配置
        config = {
            "api_key": GLOBAL_MODEL_API_KEY,
            "base_url": GLOBAL_MODEL_BASE_URL,
            "model": GLOBAL_MODEL_ID,
            "max_tokens": max_tokens
        }

        # 节点特定映射
        if node_name == "gateway":
            config["api_key"] = GATEWAY_MODEL_API_KEY
            config["base_url"] = GATEWAY_MODEL_BASE_URL
            config["model"] = GATEWAY_MODEL_ID
        elif node_name == "analyst":
            config["api_key"] = ANALYST_MODEL_API_KEY
            config["base_url"] = ANALYST_MODEL_BASE_URL
            config["model"] = ANALYST_MODEL_ID
        elif node_name == "researcher":
            config["api_key"] = RESEARCHER_MODEL_API_KEY
            config["base_url"] = RESEARCHER_MODEL_BASE_URL
            config["model"] = RESEARCHER_MODEL_ID

        return ChatOpenAI(
            api_key=SecretStr(config["api_key"]) if config["api_key"] else None,
            base_url=config["base_url"],
            model=config["model"],
            temperature=temperature,
            streaming=streaming
        )
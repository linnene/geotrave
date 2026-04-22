"""
Module: src.utils.llm_factory
Responsibility: Centralized factory for creating and configuring LLM instances.
"""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from utils.config import (
    GLOBAL_MODEL_API_KEY, 
    GLOBAL_MODEL_BASE_URL, 
    GLOBAL_MODEL_ID,
    ROUTER_MODEL_API_KEY,
    ROUTER_MODEL_BASE_URL,
    ROUTER_MODEL_ID,
    ANALYZER_MODEL_API_KEY,
    ANALYZER_MODEL_BASE_URL,
    ANALYZER_MODEL_ID,
    RESEARCHER_MODEL_API_KEY,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_ID
)

class LLMFactory:
    """
    LLM 实例工厂，支持按节点名称获取定制配置的 LLM。
    """
    
    @staticmethod
    def get_model(node_name: str, temperature: float = 0, streaming: bool = False):
        """
        根据节点名称返回对应的 ChatOpenAI 实例。
        """
        # 默认配置
        config = {
            "api_key": GLOBAL_MODEL_API_KEY,
            "base_url": GLOBAL_MODEL_BASE_URL,
            "model": GLOBAL_MODEL_ID
        }

        # 节点特定映射
        if node_name == "gateway":
            config["api_key"] = ROUTER_MODEL_API_KEY
            config["base_url"] = ROUTER_MODEL_BASE_URL
            config["model"] = ROUTER_MODEL_ID
        elif node_name == "analyst":
            config["api_key"] = ANALYZER_MODEL_API_KEY
            config["base_url"] = ANALYZER_MODEL_BASE_URL
            config["model"] = ANALYZER_MODEL_ID
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
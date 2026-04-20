"""
Module: src.utils.llm_factory
Responsibility: Centralized factory for instantiating LangChain ChatOpenAI models with node-specific configurations.
Parent Module: src.utils
Dependencies: langchain_openai, src.utils.config, pydantic

This factory ensures that all nodes (Router, Analyzer, Researcher, etc.) use consistent 
initialization patterns while adhering to their specific model IDs and parameters.
"""

from typing import Literal
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from src.utils.config import (
    ROUTER_MODEL_API_KEY, 
    ROUTER_MODEL_BASE_URL, 
    ROUTER_MODEL_ID,
    ANALYZER_MODEL_API_KEY,
    ANALYZER_MODEL_BASE_URL,
    ANALYZER_MODEL_ID,
    RESEARCHER_MODEL_API_KEY,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

NodeType = Literal["router", "analyzer", "researcher"]

class LLMFactory:
    """
    Unified entry point for LLM creation.
    """
    
    @staticmethod
    def get_model(
        node_type: NodeType, 
        temperature: float = PLANNING_TEMPERATURE,
        streaming: bool = False
    ) -> ChatOpenAI:
        """
        Returns a configured ChatOpenAI instance based on the node type.
        """
        if node_type == "router":
            return ChatOpenAI(
                model=ROUTER_MODEL_ID,
                api_key=SecretStr(ROUTER_MODEL_API_KEY),
                base_url=ROUTER_MODEL_BASE_URL,
                temperature=0.0,  # Router usually needs high determinism
                max_completion_tokens=MAX_TOKENS,
                timeout=LLM_TIMEOUT,
                disable_streaming=not streaming,
            )
        elif node_type == "analyzer":
            return ChatOpenAI(
                model=ANALYZER_MODEL_ID,
                api_key=SecretStr(ANALYZER_MODEL_API_KEY),
                base_url=ANALYZER_MODEL_BASE_URL,
                temperature=temperature,
                max_completion_tokens=MAX_TOKENS,
                timeout=LLM_TIMEOUT,
                disable_streaming=not streaming,
            )
        elif node_type == "researcher":
            return ChatOpenAI(
                model=RESEARCHER_MODEL_ID,
                api_key=SecretStr(RESEARCHER_MODEL_API_KEY),
                base_url=RESEARCHER_MODEL_BASE_URL,
                temperature=temperature,
                max_completion_tokens=MAX_TOKENS,
                timeout=LLM_TIMEOUT,
                disable_streaming=not streaming,
            )
        else:
            raise ValueError(f"Unsupported node type: {node_type}")

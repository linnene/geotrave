"""
LLM Factory Module for GeoTrave.

This module provides a centralized factory to create LangChain LLM instances
based on node-specific configurations. It ensures consistent initialization
and reduces code duplication across agent nodes.

Parent Module: src.agent
Dependencies: langchain_openai, utils.config
"""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from utils.config import (
    ANALYZER_MODEL_API_KEY, ANALYZER_MODEL_BASE_URL, ANALYZER_MODEL_ID,
    RESEARCHER_MODEL_API_KEY, RESEARCHER_MODEL_BASE_URL, RESEARCHER_MODEL_ID,
    ROUTER_MODEL_API_KEY, ROUTER_MODEL_BASE_URL, ROUTER_MODEL_ID,
    PLANNER_MODEL_API_KEY, PLANNER_MODEL_BASE_URL, PLANNER_MODEL_ID,
    PLANNING_TEMPERATURE, MAX_TOKENS, LLM_TIMEOUT
)

class LLMFactory:
    """Factory class to create and manage LLM instances."""

    @staticmethod
    def create_analyzer_llm() -> ChatOpenAI:
        """Create LLM instance for the Analyzer node."""
        return ChatOpenAI(
            model=ANALYZER_MODEL_ID,
            api_key=SecretStr(ANALYZER_MODEL_API_KEY),
            base_url=ANALYZER_MODEL_BASE_URL,
            temperature=PLANNING_TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            disable_streaming=True
        )

    @staticmethod
    def create_researcher_llm() -> ChatOpenAI:
        """Create LLM instance for the Researcher node."""
        return ChatOpenAI(
            model=RESEARCHER_MODEL_ID,
            api_key=SecretStr(RESEARCHER_MODEL_API_KEY),
            base_url=RESEARCHER_MODEL_BASE_URL,
            temperature=PLANNING_TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            disable_streaming=True
        )

    @staticmethod
    def create_router_llm() -> ChatOpenAI:
        """Create LLM instance for the Router node."""
        return ChatOpenAI(
            model=ROUTER_MODEL_ID,
            api_key=SecretStr(ROUTER_MODEL_API_KEY),
            base_url=ROUTER_MODEL_BASE_URL,
            temperature=0.0,  # Router needs deterministic output
            max_completion_tokens=500,
            timeout=LLM_TIMEOUT,
            disable_streaming=True
        )

    @staticmethod
    def create_planner_llm() -> ChatOpenAI:
        """Create LLM instance for the Planner node."""
        return ChatOpenAI(
            model=PLANNER_MODEL_ID,
            api_key=SecretStr(PLANNER_MODEL_API_KEY),
            base_url=PLANNER_MODEL_BASE_URL,
            temperature=PLANNING_TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            disable_streaming=True
        )

"""
Module: src.utils
Responsibility: Aggregates and unconditionally exposes core infrastructure utilities.
Parent Module: src
Dependencies: src.utils.config, src.utils.logger, src.utils.prompt

This guarantees robust single-point imports for the entire application, maintaining
a unidirectional dependency graph (e.g., `from src.utils import logger, config`).
"""

# Explicitly expose infrastructure utilities
from src.utils.logger import logger, get_logger
from src.utils.config import (
    LOG_LEVEL,
    CHROMA_DB_DIR,
    DB_TIMEOUT, # Additional configs can be managed here collectively
    EMBEDDING_MODEL_API_KEY,
    EMBEDDING_MODEL_BASE_URL,
    EMBEDDING_MODEL,
    ANALYZER_MODEL_API_KEY,
    ANALYZER_MODEL_BASE_URL,
    ANALYZER_MODEL_ID,
    RESEARCHER_MODEL_API_KEY,
    RESEARCHER_MODEL_BASE_URL,
    RESEARCHER_MODEL_ID,
    ROUTER_MODEL_API_KEY,
    ROUTER_MODEL_BASE_URL,
    ROUTER_MODEL_ID,
)
from src.utils.prompt import (
    router_prompt_template,
    analyzer_prompt_template,
    research_query_prompt_template,
    research_batch_filter_prompt_template,
)

__all__ = [
    "logger",
    "get_logger",
    
    # Pre-exported frequently accessed config constants
    "CHROMA_DB_DIR",
    "DB_TIMEOUT",
    "LOG_LEVEL",
    
    # Embedding Configuration
    "EMBEDDING_MODEL",
    "EMBEDDING_MODEL_API_KEY",
    "EMBEDDING_MODEL_BASE_URL",
    
    # Models Configurations
    "ANALYZER_MODEL_API_KEY",
    "ANALYZER_MODEL_BASE_URL",
    "ANALYZER_MODEL_ID",
    "RESEARCHER_MODEL_API_KEY",
    "RESEARCHER_MODEL_BASE_URL",
    "RESEARCHER_MODEL_ID",
    "ROUTER_MODEL_API_KEY",
    "ROUTER_MODEL_BASE_URL",
    "ROUTER_MODEL_ID",
    
    # Prompts
    "router_prompt_template",
    "analyzer_prompt_template",
    "research_query_prompt_template",
    "research_batch_filter_prompt_template",
]

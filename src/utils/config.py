"""
Module: src.utils.config
Responsibility: Centralized configuration management handling environment variables, LLM parameters, and system-wide settings.
Parent Module: src.utils
Dependencies: os, python-dotenv

This module loads the `.env` file and exposes immutable global configurations 
for database connections, LLM APIs, and agent hyperparameters.
"""

import os
from dotenv import load_dotenv

# ==============================================================================
# GeoTrave Configuration 
# Loaded via .env file or Environment Variables
# ==============================================================================
load_dotenv()

# --- 1. Global LLM Configuration ---
# If configured, acts as a fallback for any node that does not have specific configs
GLOBAL_MODEL_API_KEY = os.getenv("GLOBAL_MODEL_API_KEY", "")
GLOBAL_MODEL_BASE_URL = os.getenv("GLOBAL_MODEL_BASE_URL", "")
GLOBAL_MODEL_ID = os.getenv("GLOBAL_MODEL_ID", "")

# --- 2. Node-Specific LLM Configuration ---
# Analyzer (分析师)
ANALYZER_MODEL_API_KEY = os.getenv("ANALYZER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ANALYZER_MODEL_BASE_URL = os.getenv("ANALYZER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ANALYZER_MODEL_ID = os.getenv("ANALYZER_MODEL_ID", GLOBAL_MODEL_ID)

# Researcher (研究员)
RESEARCHER_MODEL_API_KEY = os.getenv("RESEARCHER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
RESEARCHER_MODEL_BASE_URL = os.getenv("RESEARCHER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
RESEARCHER_MODEL_ID = os.getenv("RESEARCHER_MODEL_ID", GLOBAL_MODEL_ID)

# Router (网关)
ROUTER_MODEL_API_KEY = os.getenv("ROUTER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ROUTER_MODEL_BASE_URL = os.getenv("ROUTER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ROUTER_MODEL_ID = os.getenv("ROUTER_MODEL_ID", GLOBAL_MODEL_ID)

# Planner (规划师) (预留)
PLANNER_MODEL_API_KEY = os.getenv("PLANNER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
PLANNER_MODEL_BASE_URL = os.getenv("PLANNER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
PLANNER_MODEL_ID = os.getenv("PLANNER_MODEL_ID", GLOBAL_MODEL_ID)

# --- 3. Embedding (知识库向量模型) ---
EMBEDDING_MODEL_API_KEY = os.getenv("EMBEDDING_MODEL_API_KEY", "")
EMBEDDING_MODEL_BASE_URL = os.getenv("EMBEDDING_MODEL_BASE_URL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

# --- 4. Agent Tuning Parameters ---
PLANNING_TEMPERATURE = 0.7
MAX_TOKENS = 4096
LLM_TIMEOUT = 60

# --- 5. System Base Configuration ---
# ChromaDB 向量数据库配置
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./data/chroma")
DB_TIMEOUT = 60

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

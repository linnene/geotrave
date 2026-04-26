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
GLOBAL_MODEL_API_KEY = os.getenv("GLOBAL_MODEL_API_KEY", "")
GLOBAL_MODEL_BASE_URL = os.getenv("GLOBAL_MODEL_BASE_URL", "")
GLOBAL_MODEL_ID = os.getenv("GLOBAL_MODEL_ID", "")

# --- 2. Node-Specific LLM Configuration ---
ANALYST_MODEL_API_KEY = os.getenv("ANALYZER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ANALYST_MODEL_BASE_URL = os.getenv("ANALYZER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ANALYST_MODEL_ID = os.getenv("ANALYZER_MODEL_ID", GLOBAL_MODEL_ID)

RESEARCHER_MODEL_API_KEY = os.getenv("RESEARCHER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
RESEARCHER_MODEL_BASE_URL = os.getenv("RESEARCHER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
RESEARCHER_MODEL_ID = os.getenv("RESEARCHER_MODEL_ID", GLOBAL_MODEL_ID)

GATEWAY_MODEL_API_KEY = os.getenv("ROUTER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
GATEWAY_MODEL_BASE_URL = os.getenv("ROUTER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
GATEWAY_MODEL_ID = os.getenv("ROUTER_MODEL_ID", GLOBAL_MODEL_ID)

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
# Checkpoint 数据库配置 (Sqlite)
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "data/checkpointer/checkpoints.sqlite")

# ChromaDB 向量数据库配置
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./data/chroma")
DB_TIMEOUT = 60

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
